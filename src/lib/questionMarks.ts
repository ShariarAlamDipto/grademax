// Server-side lookup of each question's marks. Client components import the
// pure helpers from './questionMarksTotal' instead, so these tables
// (about 10,000 entries) stay out of the browser bundle.
import commerceMarks from './commerceQuestionMarks.json'
import computerScienceMarks from './computerScienceQuestionMarks.json'
import ialAccountingMarks from './ialAccountingQuestionMarks.json'
import ialBusinessMarks from './ialBusinessQuestionMarks.json'
import ictMarks from './ictQuestionMarks.json'
// Marks printed on each question paper ("Total for Question N is M marks"),
// one file per subject. Regenerate with
// scripts/extract_printed_question_marks.py --subject <CODE>.
import printed4AC1 from './printedMarks/4AC1.json'
import printed4BI1 from './printedMarks/4BI1.json'
import printed4BS1 from './printedMarks/4BS1.json'
import printed4CH1 from './printedMarks/4CH1.json'
import printed4CP1 from './printedMarks/4CP1.json'
import printed4EC1 from './printedMarks/4EC1.json'
import printed4HB1 from './printedMarks/4HB1.json'
import printed4MA1 from './printedMarks/4MA1.json'
import printed4MB1 from './printedMarks/4MB1.json'
import printed4PH1 from './printedMarks/4PH1.json'
import printed4PM1 from './printedMarks/4PM1.json'
import printedWMA11 from './printedMarks/WMA11.json'
import printedWMA12 from './printedMarks/WMA12.json'
import printedWMA13 from './printedMarks/WMA13.json'
import printedWMA14 from './printedMarks/WMA14.json'
import printedWME01 from './printedMarks/WME01.json'
import printedWST01 from './printedMarks/WST01.json'
// Cambridge 0625 P42/P62: each question's proven "[Total: X]"
// (scripts/onboard_cambridge_physics.py marks).
import printed0625 from './printedMarks/0625.json'

export { totalQuestionMarks, allQuestionMarksKnown } from './questionMarksTotal'

const knownMarks: Readonly<Record<string, number>> = {
  ...printed4AC1, ...printed4BI1, ...printed4BS1, ...printed4CH1, ...printed4CP1,
  ...printed4EC1, ...printed4HB1, ...printed4MA1, ...printed4MB1, ...printed4PH1,
  ...printed4PM1, ...printedWMA11, ...printedWMA12, ...printedWMA13, ...printedWMA14,
  ...printedWME01, ...printedWST01, ...printed0625,
  // Hand-made tables; they agree with the printed totals and win on a clash.
  ...commerceMarks, ...computerScienceMarks, ...ialAccountingMarks, ...ialBusinessMarks, ...ictMarks,
}

export function getQuestionMarks(paperId: string, questionNumber: string): number | null {
  return knownMarks[`${paperId}|${questionNumber}`] ?? null
}
