import test from "node:test";
import assert from "node:assert/strict";
import * as PdfLib from "pdf-lib";
import {
  assembleQuestionPdfs,
  planQuestionSources,
  questionLabel,
} from "../src/lib/questionPdfAssembly";

/** A source PDF whose page size encodes which question it belongs to. */
async function fakeQuestionPdf(questionId: number, pages = 1): Promise<ArrayBuffer> {
  const doc = await PdfLib.PDFDocument.create();
  for (let i = 0; i < pages; i++) doc.addPage([400 + questionId, 500]);
  const bytes = await doc.save();
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

const worksheet = [
  { qpPageUrl: "qp/1", msPageUrl: "ms/1", questionNumber: "3", year: 2019, season: "may-jun", paper: "1R" },
  { qpPageUrl: "qp/2", msPageUrl: null, questionNumber: "7", year: 2021, season: "jan", paper: "2" },
  { qpPageUrl: "qp/3", msPageUrl: "ms/3", questionNumber: "1", year: 2023, season: "oct-nov", paper: "1" },
];

test("a question without a mark scheme keeps its slot", () => {
  const sources = planQuestionSources(worksheet, "markscheme");
  assert.equal(sources.length, 3, "no question may be filtered out");
  assert.deepEqual(sources.map((s) => s.url), ["ms/1", null, "ms/3"]);
});

test("labels name the worksheet position and the source question", () => {
  assert.equal(
    questionLabel(1, worksheet[0]),
    "Q1 · 2019 May/Jun · Paper 1R · Question 3",
  );
  assert.equal(questionLabel(4), "Q4");
  assert.equal(
    planQuestionSources(worksheet, "worksheet")[2].label,
    "Q3 · 2023 Oct/Nov · Paper 1 · Question 1",
  );
});

test("missing and failed mark schemes become placeholders, never a shift", async () => {
  const bodies: Record<string, ArrayBuffer | null> = {
    "ms/1": await fakeQuestionPdf(1),
    "ms/3": await fakeQuestionPdf(3, 2),
  };
  const doc = await PdfLib.PDFDocument.create();
  const result = await assembleQuestionPdfs(
    doc,
    PdfLib,
    planQuestionSources(worksheet, "markscheme"),
    "markscheme",
    async (url) => bodies[url] ?? null,
  );

  assert.deepEqual(result, { merged: 2, placeholders: 1 });
  // q1 (1 page) + q2 placeholder (1 page) + q3 (2 pages)
  assert.equal(doc.getPageCount(), 4);
});

test("a download that fails is a placeholder in the same slot", async () => {
  const doc = await PdfLib.PDFDocument.create();
  const good = await fakeQuestionPdf(1);
  const result = await assembleQuestionPdfs(
    doc,
    PdfLib,
    [
      { url: "broken", label: "Q1" },
      { url: "good", label: "Q2" },
    ],
    "worksheet",
    async (url) => {
      if (url === "broken") throw new Error("network");
      return good;
    },
  );
  assert.deepEqual(result, { merged: 1, placeholders: 1 });
  assert.equal(doc.getPageCount(), 2);
});

test("garbage bytes are a placeholder, not a crash", async () => {
  const doc = await PdfLib.PDFDocument.create();
  const junk = new TextEncoder().encode("<html>login</html>").buffer as ArrayBuffer;
  const result = await assembleQuestionPdfs(
    doc,
    PdfLib,
    [{ url: "x", label: "Q1" }],
    "markscheme",
    async () => junk,
  );
  assert.deepEqual(result, { merged: 0, placeholders: 1 });
  assert.equal(doc.getPageCount(), 1);
});
