import { subjects, boardOf, levelShort, type Board, type Level } from "@/lib/subjects"
import { seoSubjects, isSingleUnitEdexcelCode } from "@/lib/seo-subjects"
import { getPapersIndex } from "@/lib/papersIndex"

// Data for the head-term hub pages (/edexcel-past-papers, /edexcel-igcse-past-papers,
// /edexcel-a-level-past-papers). These pages ranked far worse than deep session
// pages partly because they under-linked the /past-papers tree. Everything here is
// filtered against the DB-backed papers index so we only ever link subjects/years
// that actually have papers — no soft-404 links for Googlebot.

export interface HubSubjectEntry {
  slug: string
  name: string
  level: Level
  /** Years with at least one published paper, descending. */
  years: number[]
}

export interface ExamCodeRef {
  code: string
  /** e.g. "IGCSE Physics" */
  subjectLabel: string
  /** /past-papers/{slug} */
  slug: string
}

export interface HubData {
  subjects: HubSubjectEntry[]
  codeRefs: ExamCodeRef[]
}

/**
 * Subjects (optionally filtered by level) that actually have published papers,
 * each with its available years, plus a single-unit exam-code → subject map for
 * the paper-code reference table. One index read serves both.
 *
 * `board` defaults to "edexcel" — these hubs are Edexcel head-term pages and
 * must not leak Cambridge subjects into their catalogs.
 */
export async function getHubData(level?: Level, board: Board = "edexcel"): Promise<HubData> {
  const { yearsBySubject } = await getPapersIndex()
  const yearsFor = (slug: string): number[] =>
    Array.from(yearsBySubject.get(slug) ?? []).sort((a, b) => b - a)
  const hasPapers = (slug: string): boolean => (yearsBySubject.get(slug)?.size ?? 0) > 0

  const subjectEntries: HubSubjectEntry[] = subjects
    .filter((s) => boardOf(s.level) === board && (!level || s.level === level) && hasPapers(s.slug))
    .map((s) => ({ slug: s.slug, name: s.name, level: s.level, years: yearsFor(s.slug) }))
    .sort((a, b) => a.name.localeCompare(b.name))

  // Edexcel: single-unit qualification codes from the curated SEO subjects.
  // Cambridge: every verified subject carries its CAIE syllabus code directly.
  const codeRefs: ExamCodeRef[] =
    board === "cambridge"
      ? subjects
          .filter(
            (s) =>
              boardOf(s.level) === "cambridge" &&
              (!level || s.level === level) &&
              Boolean(s.examCode) &&
              hasPapers(s.slug),
          )
          .map((s) => ({
            code: s.examCode as string,
            subjectLabel: `${levelShort(s.level)} ${s.name}`,
            slug: s.slug,
          }))
          .sort((a, b) => a.code.localeCompare(b.code))
      : seoSubjects
          .filter(
            (s) =>
              (!level || s.level === level) &&
              isSingleUnitEdexcelCode(s.examCode) &&
              !s.name.startsWith("IAL ") &&
              hasPapers(s.slug),
          )
          .map((s) => ({ code: s.examCode, subjectLabel: `${s.levelDisplay} ${s.name}`, slug: s.slug }))
          .sort((a, b) => a.code.localeCompare(b.code))

  return { subjects: subjectEntries, codeRefs }
}
