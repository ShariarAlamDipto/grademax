"use client"
import { useEffect, useState } from "react"
import { MAX_QUESTIONS_PER_PAPER, type QuestionLimit } from "./toolLimits"

// The signed-in user's per-paper question limit (null = no limit). Starts at
// the normal-student limit and widens once the server confirms otherwise.
export function useQuestionLimit(): { limit: QuestionLimit; proUntil: string | null } {
  const [state, setState] = useState<{ limit: QuestionLimit; proUntil: string | null }>({
    limit: MAX_QUESTIONS_PER_PAPER,
    proUntil: null,
  })

  useEffect(() => {
    let cancelled = false
    fetch("/api/tools/question-limit")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return
        const limit = data.limit === null ? null : Number(data.limit) || MAX_QUESTIONS_PER_PAPER
        setState({ limit, proUntil: typeof data.proUntil === "string" ? data.proUntil : null })
      })
      .catch(() => {
        // Keep the student limit; the server enforces the real one anyway.
      })
    return () => { cancelled = true }
  }, [])

  return state
}
