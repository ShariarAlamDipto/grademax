import test from "node:test";
import assert from "node:assert/strict";
import * as PdfLib from "pdf-lib";
import {
  assembleQuestionPdfs,
  planQuestionSources,
  questionLabel,
} from "../src/lib/questionPdfAssembly";

/** A source PDF whose page size encodes which question it belongs to. */
async function fakeQuestionPdf(questionId: number, pages = 1, height = 500): Promise<ArrayBuffer> {
  const doc = await PdfLib.PDFDocument.create();
  for (let i = 0; i < pages; i++) doc.addPage([400 + questionId, height]);
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
  // q1 (500pt) and the q2 placeholder share a sheet; each 500pt q3 page needs its own.
  assert.equal(doc.getPageCount(), 3);
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
  // The placeholder block and the 500pt question fit on one sheet, in slot order.
  assert.equal(doc.getPageCount(), 1);
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

async function layoutOf(heights: number[][]): Promise<{ sheets: number; blocks: import("../src/lib/questionPdfAssembly").PlacedBlock[] }> {
  const doc = await PdfLib.PDFDocument.create();
  const bodies = await Promise.all(heights.map(async (pages, q) => {
    const src = await PdfLib.PDFDocument.create();
    for (const h of pages) src.addPage([595, h]);
    const bytes = await src.save();
    return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  }));
  let blocks: import("../src/lib/questionPdfAssembly").PlacedBlock[] = [];
  await assembleQuestionPdfs(
    doc, PdfLib,
    heights.map((_, q) => ({ url: String(q), label: `Q${q + 1}` })),
    "worksheet",
    async (url) => bodies[Number(url)],
    undefined, undefined,
    (placed) => { blocks = [...placed]; },
  );
  return { sheets: doc.getPageCount(), blocks };
}

test("short MCQ strips share a sheet instead of one sheet each", async () => {
  const { sheets, blocks } = await layoutOf(Array.from({ length: 8 }, () => [160]));
  assert.equal(sheets, 2, "eight 160pt strips fit on two A4 sheets, not eight");
  assert.deepEqual(blocks.map((b) => b.question), [0, 1, 2, 3, 4, 5, 6, 7], "slot order is kept");
  for (const b of blocks) assert.ok(b.bottom >= 24, "no block runs into the bottom margin");
});

test("blocks on one sheet never overlap and run top to bottom", async () => {
  const { blocks } = await layoutOf([[160], [300], [200], [160]]);
  for (let i = 1; i < blocks.length; i++) {
    if (blocks[i].sheet !== blocks[i - 1].sheet) continue;
    assert.ok(blocks[i].top < blocks[i - 1].bottom, `block ${i} starts below block ${i - 1}`);
  }
});

test("a full-height page always gets its own sheet", async () => {
  const { sheets, blocks } = await layoutOf([[160], [842], [160]]);
  assert.equal(sheets, 3);
  assert.deepEqual(blocks.map((b) => b.sheet), [0, 1, 2]);
});

test("a short last page of a long question is followed by the next question", async () => {
  const { sheets, blocks } = await layoutOf([[842, 300], [160]]);
  assert.equal(sheets, 2, "the 300pt continuation and the next MCQ share the second sheet");
  assert.deepEqual(blocks.map((b) => [b.question, b.sheet]), [[0, 0], [0, 1], [1, 1]]);
});
