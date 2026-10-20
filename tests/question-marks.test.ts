import { test } from 'node:test'
import assert from 'node:assert/strict'
import { totalQuestionMarks, getQuestionMarks } from '../src/lib/questionMarks'
import commerceMarks from '../src/lib/commerceQuestionMarks.json'

test('whole commerce questions use their actual marks on PDF covers', () => {
  assert.equal(totalQuestionMarks([{ marks: 20 }, { marks: 20 }]), 40)
  assert.equal(totalQuestionMarks([{ marks: 1 }, { marks: 5 }, { marks: 15 }]), 21)
  assert.equal(totalQuestionMarks([{ marks: 25 }, { marks: 25 }]), 50)
})

test('legacy questions retain their estimate and invalid stored marks are ignored', () => {
  assert.equal(totalQuestionMarks([{ marks: null }, {}, { marks: -1 }, { marks: NaN }]), 16)
  assert.equal(totalQuestionMarks([]), 0)
})

test('verified marks belong to a specific paper and question', () => {
  const [key, marks] = Object.entries(commerceMarks)[0]
  const [paper, number] = key.split('|')
  assert.equal(getQuestionMarks(paper, number), marks)
  assert.equal(getQuestionMarks('other-paper', number), null)
  assert.equal(getQuestionMarks(paper, '999'), null)
})
