import { test } from 'node:test'
import assert from 'node:assert/strict'
import { TOOL_SUBJECT_SLOTS, isToolSubjectCode } from '../src/lib/toolSubjects'

test('every tool subject slot code, including legacy variants, has question-level data', () => {
  for (const code of TOOL_SUBJECT_SLOTS.flat()) assert.equal(isToolSubjectCode(code), true, code)
})

test('Maths A, S1 and P1-P4 are tool subjects for the AI connector', () => {
  for (const code of ['4MA1', 'WST01', 'WMA11', 'WMA12', 'WMA13', 'WMA14']) {
    assert.equal(isToolSubjectCode(code), true, code)
  }
})

test('download-only and missing codes are not tool subjects', () => {
  for (const code of ['4ME1', '9702', '', null, undefined]) {
    assert.equal(isToolSubjectCode(code), false, String(code))
  }
})
