/**
 * Limits on the worksheet generator, shared by the form and the API so the two
 * can never disagree. The API enforces them; the form only reflects them.
 */

/** Most questions one generated worksheet may hold. */
export const MAX_WORKSHEET_QUESTIONS = 20

/**
 * Worksheets one signed-in user may generate. Each one hands out up to
 * 2 × MAX_WORKSHEET_QUESTIONS page PDFs, so this is what stops the generator
 * being used to copy the chapterwise question bank wholesale.
 */
export const WORKSHEET_RATE_LIMITS = [
  { limit: 10, windowSeconds: 600 },     // per 10 minutes
  { limit: 40, windowSeconds: 86_400 },  // per day
]
