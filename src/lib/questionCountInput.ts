/**
 * Turn what a student typed into a question count within [1, max].
 *
 * Applied when the field loses focus, not on every keystroke: clamping while
 * typing snapped an emptied field straight back to the fallback, so a phone
 * user could never clear "20" to type "15".
 */
export function parseQuestionCount(raw: string, max: number, fallback: number): number {
  const parsed = Number.parseInt(raw, 10);
  const value = Number.isNaN(parsed) ? fallback : parsed;
  return Math.min(max, Math.max(1, value));
}
