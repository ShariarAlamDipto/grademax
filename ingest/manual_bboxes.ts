/**
 * Manual bbox overrides for questions that are hard to detect automatically
 * Format: { questionNumber: { page, x, y, width, height } }
 */
export const MANUAL_BBOX_OVERRIDES: Record<string, { page: number; x: number; y: number; width: number; height: number }> = {
  // Question 2: Located around page 3 based on text parser output
  // This is a placeholder - will be refined after viewing the actual PDF page
  '2': {
    page: 3,
    x: 40,
    y: 100,
    width: 515,
    height: 600
  },
  
  // Question 4: Located around page 5-6 based on text parser output
  '4': {
    page: 6,
    x: 40,
    y: 100,
    width: 515,
    height: 700
  }
}
