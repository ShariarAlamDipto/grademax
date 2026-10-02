import { test } from "node:test"
import assert from "node:assert/strict"

import {
  R2_PUBLIC_HOST,
  absoluteGatedPdfUrl,
  buildViewerHref,
  gatedPdfHref,
  isSafePdfKey,
  r2KeyFromUrl,
  resolveViewerPdfParam,
} from "../src/lib/viewer-link"

const R2 = `https://${R2_PUBLIC_HOST}`
const paper = `${R2}/Physics/2019/May-Jun/Paper%201%20QP.pdf`

test("a bucket URL yields its decoded key", () => {
  assert.equal(r2KeyFromUrl(paper), "Physics/2019/May-Jun/Paper 1 QP.pdf")
})

test("other hosts and non-PDFs are not bucket keys", () => {
  assert.equal(r2KeyFromUrl("https://evil.example/Physics/a.pdf"), null)
  assert.equal(r2KeyFromUrl(`http://${R2_PUBLIC_HOST}/a.pdf`), null)
  assert.equal(r2KeyFromUrl(`${R2}/store/book/cover.jpg`), null)
  assert.equal(r2KeyFromUrl(null), null)
})

test("keys cannot climb out of the bucket", () => {
  for (const bad of ["../secret.pdf", "a/../b.pdf", "/abs.pdf", "a//b.pdf", "a\\b.pdf", "a/./b.pdf", ""]) {
    assert.equal(isSafePdfKey(bad), false, bad)
  }
  assert.equal(isSafePdfKey(`${"a/".repeat(300)}x.pdf`), false)
  // The URL parser resolves encoded dot-segments before we read the path, so
  // what comes out is an ordinary key inside the bucket.
  assert.equal(r2KeyFromUrl(`${R2}/a/%2E%2E/b.pdf`), "b.pdf")
  assert.equal(isSafePdfKey(decodeURIComponent("a/%2E%2E/b.pdf")), false)
})

test("downloads go through the gate, never the bucket host", () => {
  assert.equal(gatedPdfHref(paper), "/api/pdf/Physics/2019/May-Jun/Paper%201%20QP.pdf")
  assert.equal(gatedPdfHref(paper, { download: true }), "/api/pdf/Physics/2019/May-Jun/Paper%201%20QP.pdf?dl=1")
  assert.equal(
    absoluteGatedPdfUrl(paper, "https://www.grademax.me"),
    "https://www.grademax.me/api/pdf/Physics/2019/May-Jun/Paper%201%20QP.pdf"
  )
})

test("legacy Supabase files pass through; unknown hosts are dropped", () => {
  const supa = "https://abc.supabase.co/storage/v1/object/public/question-pdfs/q1.pdf"
  assert.equal(gatedPdfHref(supa), supa)
  assert.equal(absoluteGatedPdfUrl(supa, "https://www.grademax.me"), supa)
  assert.equal(gatedPdfHref("https://evil.example/a.pdf"), null)
})

test("viewer links carry keys, and the viewer reads both keys and old URLs", () => {
  const href = buildViewerHref({ doc: "qp", qpUrl: paper, msUrl: null, title: "P1", backPath: "/past-papers" })
  assert.ok(!href.includes(R2_PUBLIC_HOST), href)
  const qp = new URLSearchParams(href.split("?")[1]).get("qp")
  assert.equal(qp, "Physics/2019/May-Jun/Paper 1 QP.pdf")
  assert.equal(resolveViewerPdfParam(qp), paper)
  assert.equal(resolveViewerPdfParam(paper), paper)
  assert.equal(resolveViewerPdfParam("https://evil.example/a.pdf"), null)
  assert.equal(resolveViewerPdfParam("../x.pdf"), null)
})
