// Public, read-only MCP connector for grademax.me.
//
// Exposes the past-paper catalog to the Claude app (and any MCP client) over
// the Streamable HTTP transport at /api/mcp. No auth: every tool reads only
// data that is already public on the site, via src/lib/mcp/catalog.ts (which
// reads the build-time papers index — no Supabase round-trip, no service-role
// key, no cookie-authed /api routes).
//
// Add in Claude: Settings → Connectors → Add custom connector →
//   https://www.grademax.me/api/mcp
//
// The route lives at /api/[transport] so the Streamable HTTP endpoint resolves
// to the clean URL /api/mcp (transport = "mcp"). Static /api/* routes
// (/api/papers, /api/subjects, …) take precedence over this dynamic segment;
// only otherwise-undefined /api/<x> paths fall through to the handler's 404.
//
// Local testing:
//   npx @modelcontextprotocol/inspector    # point it at http://localhost:3000/api/mcp

import { createMcpHandler } from "mcp-handler"
import { z } from "zod"
import {
  listSubjects,
  searchPapers,
  getPaper,
  VALID_SEASONS,
} from "@/lib/mcp/catalog"
import {
  listTopics,
  searchQuestions,
  buildPracticeTest,
  DIFFICULTIES,
} from "@/lib/mcp/questions"

// catalog.ts reads a local file via node:fs; keep this off the Edge runtime.
export const runtime = "nodejs"
export const dynamic = "force-dynamic"
export const maxDuration = 60

const boardEnum = z.enum(["edexcel", "cambridge"])
const levelEnum = z.enum(["igcse", "ial", "cambridge-igcse", "cambridge-a-level"])
const seasonEnum = z.enum(VALID_SEASONS)
const difficultyEnum = z.enum(DIFFICULTIES)

function json(data: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] }
}

function error(message: string) {
  return { content: [{ type: "text" as const, text: message }], isError: true }
}

const handler = createMcpHandler(
  (server) => {
    server.registerTool(
      "list_subjects",
      {
        title: "List GradeMax subjects",
        description:
          "List the subjects GradeMax has past papers for. Call this first when the " +
          "user asks about a subject, an exam board (Edexcel or Cambridge), or an exam " +
          "level (IGCSE, IAL/A-Level), or when you need the exact subject slug to pass " +
          "to search_papers. Optionally filter by board or level.",
        inputSchema: {
          board: boardEnum.optional().describe("Filter to one exam board."),
          level: levelEnum.optional().describe("Filter to one exam level."),
          withPapersOnly: z
            .boolean()
            .optional()
            .describe("Only return subjects that currently have published papers."),
        },
      },
      async ({ board, level, withPapersOnly }) => {
        const rows = await listSubjects({ board, level, withPapersOnly })
        return json({ count: rows.length, subjects: rows })
      }
    )

    server.registerTool(
      "search_papers",
      {
        title: "Search GradeMax past papers",
        description:
          "Find past papers (question papers + mark schemes) for a subject on " +
          "GradeMax. Call this when the user asks for a past paper, mark scheme, or " +
          "exam PDF for an Edexcel or Cambridge subject. Returns each paper with links " +
          "to the question-paper PDF, the mark-scheme PDF, and the on-site viewer. " +
          "`subject` is a slug from list_subjects (e.g. \"physics\", \"ial-chemistry\"). " +
          "Narrow with year, season, or paper as needed.",
        inputSchema: {
          subject: z
            .string()
            .describe('Subject slug from list_subjects, e.g. "physics".'),
          year: z.number().int().min(2000).max(2100).optional(),
          season: seasonEnum
            .optional()
            .describe("Exam session, e.g. may-jun, oct-nov, jan."),
          paper: z
            .string()
            .optional()
            .describe('Paper/unit/component, e.g. "1", "1R", "22", "P3".'),
          limit: z.number().int().min(1).max(100).optional(),
        },
      },
      async ({ subject, year, season, paper, limit }) => {
        const res = await searchPapers({ subject, year, season, paper, limit })
        if (!res.ok) return error(res.error)
        return json({
          subject: res.subject.name,
          subjectSlug: res.subject.slug,
          count: res.papers.length,
          papers: res.papers,
        })
      }
    )

    server.registerTool(
      "get_paper",
      {
        title: "Get one GradeMax past paper",
        description:
          "Fetch a single specific past paper by subject, year, season, and paper " +
          "number. Use this when the user names an exact paper (e.g. \"Edexcel IGCSE " +
          "Physics 2023 May-Jun Paper 1\"). Returns its question-paper PDF, mark-scheme " +
          "PDF, and viewer links. If you are unsure the paper exists, use search_papers " +
          "instead.",
        inputSchema: {
          subject: z.string().describe("Subject slug from list_subjects."),
          year: z.number().int().min(2000).max(2100),
          season: seasonEnum,
          paper: z.string().describe('Paper/unit/component, e.g. "1", "22", "P3".'),
        },
      },
      async ({ subject, year, season, paper }) => {
        const res = await getPaper({ subject, year, season, paper })
        if (!res.ok) return error(res.error)
        return json(res.paper)
      }
    )

    server.registerTool(
      "list_topics",
      {
        title: "List syllabus topics for a subject",
        description:
          "List the syllabus topics (chapters) for a subject, so you can then " +
          "filter questions by topic with search_questions. Call this when the user " +
          "wants to revise a specific chapter or topic. `subject` is a slug from " +
          "list_subjects. Note: question-level topic data exists only for these six " +
          "subjects: physics, maths-b, chemistry, biology, human-biology, " +
          "further-pure-maths. Each topic returns a `code` to pass to search_questions.",
        inputSchema: {
          subject: z.string().describe("Subject slug from list_subjects."),
        },
      },
      async ({ subject }) => {
        const res = await listTopics(subject)
        if (!res.ok) return error(res.error)
        return json({
          subject: res.subject,
          questionLevelSearchAvailable: res.classified,
          topicCount: res.topics.length,
          topics: res.topics,
        })
      }
    )

    server.registerTool(
      "search_questions",
      {
        title: "Search individual exam questions by topic",
        description:
          "Find individual past-paper questions for a subject, optionally filtered by " +
          "topic, difficulty, and year range. Use this to build topic-based revision " +
          "(e.g. \"give me hard Physics waves questions\"). Each result includes the " +
          "question-page PDF, its mark-scheme PDF, and a viewer link. Pass topic " +
          "`code`s from list_topics. Question-level data exists only for physics, " +
          "maths-b, chemistry, biology, human-biology, and further-pure-maths; other " +
          "subjects return no questions (use search_papers for whole papers instead).",
        inputSchema: {
          subject: z.string().describe("Subject slug from list_subjects."),
          topics: z
            .array(z.string())
            .optional()
            .describe("Topic codes from list_topics, e.g. [\"3\",\"4\"]."),
          difficulty: difficultyEnum.optional(),
          yearStart: z.number().int().min(2000).max(2100).optional(),
          yearEnd: z.number().int().min(2000).max(2100).optional(),
          page: z.number().int().min(1).optional(),
          limit: z.number().int().min(1).max(50).optional(),
        },
      },
      async ({ subject, topics, difficulty, yearStart, yearEnd, page, limit }) => {
        const res = await searchQuestions({
          subject,
          topics,
          difficulty,
          yearStart,
          yearEnd,
          page,
          limit,
        })
        if (!res.ok) return error(res.error)
        return json({
          subject: res.subject,
          questionLevelSearchAvailable: res.classified,
          total: res.total,
          page: res.page,
          totalPages: res.totalPages,
          count: res.questions.length,
          questions: res.questions,
        })
      }
    )

    server.registerTool(
      "build_practice_test",
      {
        title: "Build a practice test for a subject",
        description:
          "Assemble a ready-to-use practice test: given a subject and optionally " +
          "topics, difficulty, and a year range, this selects a balanced set of " +
          "questions (spread across the chosen topics and across different papers) " +
          "and returns them with question-paper and mark-scheme PDF links plus a " +
          "viewer link for each, a topic/difficulty breakdown, and a link to the " +
          "on-site test builder. Use this when the user asks you to \"make\", " +
          "\"build\", or \"put together\" a practice test, mock, or problem set. " +
          "Only the six classified subjects work: physics, maths-b, chemistry, " +
          "biology, human-biology, further-pure-maths. Pass topic codes from " +
          "list_topics; default is 10 questions (max 30).",
        inputSchema: {
          subject: z.string().describe("Subject slug from list_subjects."),
          topics: z
            .array(z.string())
            .optional()
            .describe("Topic codes from list_topics to include."),
          difficulty: difficultyEnum.optional(),
          yearStart: z.number().int().min(2000).max(2100).optional(),
          yearEnd: z.number().int().min(2000).max(2100).optional(),
          count: z
            .number()
            .int()
            .min(1)
            .max(30)
            .optional()
            .describe("How many questions to include (default 10, max 30)."),
        },
      },
      async ({ subject, topics, difficulty, yearStart, yearEnd, count }) => {
        const res = await buildPracticeTest({
          subject,
          topics,
          difficulty,
          yearStart,
          yearEnd,
          count,
        })
        if (!res.ok) return error(res.error)
        return json(res.test)
      }
    )
  },
  {
    serverInfo: { name: "grademax", version: "1.0.0" },
  },
  {
    basePath: "/api",
    // SSE is deprecated and needs Redis; run stateless Streamable HTTP only.
    disableSse: true,
    maxDuration: 60,
  }
)

export { handler as GET, handler as POST }
