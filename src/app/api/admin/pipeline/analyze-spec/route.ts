import { NextRequest, NextResponse } from "next/server"
import { requireAdmin } from "@/lib/apiAuth"

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
const MAX_SPEC_CHARS = 12000
const MAX_SUBJECT_NAME_CHARS = 120
const MAX_LEVEL_CHARS = 40
const ANTHROPIC_TIMEOUT_MS = 20000

export async function POST(req: NextRequest) {
  const authResult = await requireAdmin()
  if ("error" in authResult) return authResult.error

  const body = await req.json().catch(() => null)
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const specText = typeof body.specText === "string" ? body.specText : ""
  const subjectName = typeof body.subjectName === "string" ? body.subjectName.trim() : ""
  const level = typeof body.level === "string" ? body.level.trim() : ""

  if (!specText || !subjectName) {
    return NextResponse.json({ error: "specText and subjectName required" }, { status: 400 })
  }
  if (subjectName.length > MAX_SUBJECT_NAME_CHARS) {
    return NextResponse.json({ error: "subjectName is too long" }, { status: 400 })
  }
  if (level.length > MAX_LEVEL_CHARS) {
    return NextResponse.json({ error: "level is too long" }, { status: 400 })
  }

  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: "ANTHROPIC_API_KEY not configured" }, { status: 500 })
  }

  const prompt = `You are a curriculum expert for Edexcel ${level || "IGCSE"} examinations.

Given the following subject specification text for "${subjectName}", extract a structured list of topics suitable for classifying past paper questions.

SPECIFICATION TEXT:
${specText.slice(0, MAX_SPEC_CHARS)}

Generate a JSON array of topics with this structure:
[
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
]

Rules:
- Use sequential numeric IDs starting from "1"
- SHORT_CODE should be 3-6 uppercase letters (e.g. ALG, GEOM, TRIG)
- Extract 6-12 topics, not too few, not too granular
- Focus on main topic areas from the specification, not sub-topics
- Keywords must be terms that actually appear in exam questions
- Guardrails help the LLM avoid common misclassification errors

Return ONLY the JSON array, no explanation.`

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), ANTHROPIC_TIMEOUT_MS)

  try {
    const response = await fetch(ANTHROPIC_API_URL, {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 4096,
        messages: [{ role: "user", content: prompt }],
      }),
      signal: controller.signal,
    })

    if (!response.ok) {
      return NextResponse.json({ error: `Anthropic API error (${response.status})` }, { status: 502 })
    }

    const data = await response.json()
    const text: string = data.content?.[0]?.text ?? ""

    // Parse JSON from response
    try {
      const trimmed = text.trim()
      const jsonStart = trimmed.indexOf("[")
      const jsonEnd = trimmed.lastIndexOf("]") + 1
      if (jsonStart === -1 || jsonEnd <= jsonStart) throw new Error("No JSON array found")
      const topics = JSON.parse(trimmed.slice(jsonStart, jsonEnd))
      return NextResponse.json({ topics })
    } catch {
      return NextResponse.json({ error: "Failed to parse LLM response as JSON" }, { status: 502 })
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return NextResponse.json({ error: "Anthropic request timed out" }, { status: 504 })
    }
    return NextResponse.json({ error: "Failed to analyze specification" }, { status: 500 })
  } finally {
    clearTimeout(timeoutId)
  }
}
