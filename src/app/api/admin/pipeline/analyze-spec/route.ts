import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"
import pdfParse from "pdf-parse"

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
const GROQ_MODEL = "llama-3.3-70b-versatile"
const GROQ_TIMEOUT_MS = 30000
const MAX_SPEC_CHARS = 12000
const MAX_SUBJECT_NAME_CHARS = 120
const MAX_LEVEL_CHARS = 40

const TOPIC_SCHEMA = `[
  {
    "id": "1",
    "code": "SHORT_CODE",
    "name": "Topic Name",
    "description": "One sentence description of what this topic covers",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "guardrails": {
      "include_when": "Classify as this topic when the question focuses on...",
      "exclude_when": "Do NOT classify as this topic when..."
    }
  }
]`

const RULES = `Rules:
- Use sequential numeric IDs starting from "1"
- SHORT_CODE should be 3-6 uppercase letters (e.g. ALG, GEOM, TRIG)
- Extract 6-12 topics, not too few, not too granular
- Focus on main topic areas from the specification, not sub-topics
- Keywords must be terms that actually appear in exam questions
- Guardrails help the classifier avoid common misclassification errors
Return ONLY the JSON array, no explanation or markdown.`

export async function POST(req: NextRequest) {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const body = await req.json().catch(() => null)
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const specPdfBase64 = typeof body.specPdfBase64 === "string" ? body.specPdfBase64 : ""
  const specText = typeof body.specText === "string" ? body.specText : ""
  const subjectName = typeof body.subjectName === "string" ? body.subjectName.trim() : ""
  const level = typeof body.level === "string" ? body.level.trim() : ""

  if (!specPdfBase64 && !specText) {
    return NextResponse.json({ error: "specPdfBase64 or specText required" }, { status: 400 })
  }
  if (!subjectName) {
    return NextResponse.json({ error: "subjectName required" }, { status: 400 })
  }
  if (subjectName.length > MAX_SUBJECT_NAME_CHARS) {
    return NextResponse.json({ error: "subjectName too long" }, { status: 400 })
  }
  if (level.length > MAX_LEVEL_CHARS) {
    return NextResponse.json({ error: "level too long" }, { status: 400 })
  }

  const apiKey = process.env.GROQ_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: "GROQ_API_KEY not configured" }, { status: 500 })
  }

  // Extract text from PDF if needed
  let specContent = specText
  if (specPdfBase64) {
    try {
      const pdfBuffer = Buffer.from(specPdfBase64, "base64")
      const parsed = await pdfParse(pdfBuffer)
      specContent = parsed.text || ""
      if (!specContent.trim()) {
        return NextResponse.json({ error: "Could not extract text from PDF — try the text paste option instead" }, { status: 422 })
      }
    } catch {
      return NextResponse.json({ error: "Failed to parse PDF — try the text paste option instead" }, { status: 422 })
    }
  }

  const prompt = `You are a curriculum expert for Edexcel ${level || "IGCSE"} examinations.

Given the following subject specification text for "${subjectName}", extract a structured list of topics suitable for classifying past paper questions.

SPECIFICATION TEXT:
${specContent.slice(0, MAX_SPEC_CHARS)}

Generate a JSON array of topics with this structure:
${TOPIC_SCHEMA}

${RULES}`

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), GROQ_TIMEOUT_MS)

  try {
    const response = await fetch(GROQ_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: GROQ_MODEL,
        max_tokens: 4096,
        temperature: 0.2,
        messages: [{ role: "user", content: prompt }],
      }),
      signal: controller.signal,
    })

    if (!response.ok) {
      const errBody = await response.text().catch(() => "")
      return NextResponse.json({ error: `Groq API error (${response.status}): ${errBody.slice(0, 200)}` }, { status: 502 })
    }

    const data = await response.json()
    const text: string = data.choices?.[0]?.message?.content ?? ""

    try {
      const trimmed = text.trim()
      const jsonStart = trimmed.indexOf("[")
      const jsonEnd = trimmed.lastIndexOf("]") + 1
      if (jsonStart === -1 || jsonEnd <= jsonStart) throw new Error("No JSON array found")
      const topics = JSON.parse(trimmed.slice(jsonStart, jsonEnd))
      return NextResponse.json({ topics })
    } catch {
      return NextResponse.json({ error: "Failed to parse Groq response as JSON" }, { status: 502 })
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return NextResponse.json({ error: "Groq request timed out" }, { status: 504 })
    }
    return NextResponse.json({ error: "Failed to analyze specification" }, { status: 500 })
  } finally {
    clearTimeout(timeoutId)
  }
}
