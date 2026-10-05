import type { QuestionItem } from '@/components/test-builder/QuestionCard';

/**
 * The Test Builder basket, kept in sessionStorage so it survives the page
 * being unloaded — e.g. iOS opening a generated PDF in the same tab and the
 * student pressing Back. Storage is untrusted input, so every field is
 * re-validated on the way back in.
 */
export interface StoredBasket {
  subjectId: string;
  title: string;
  items: QuestionItem[];
}

export const BASKET_STORAGE_KEY = 'gm:test-builder:basket';

export function serializeBasket(basket: StoredBasket): string {
  return JSON.stringify(basket);
}

function isQuestionItem(value: unknown): value is QuestionItem {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === 'string' &&
    typeof v.questionNumber === 'string' &&
    Array.isArray(v.topics) && v.topics.every((t) => typeof t === 'string') &&
    typeof v.difficulty === 'string' &&
    typeof v.qpPageUrl === 'string' &&
    (v.msPageUrl === null || typeof v.msPageUrl === 'string') &&
    typeof v.hasDiagram === 'boolean' &&
    typeof v.textExcerpt === 'string' &&
    typeof v.year === 'number' &&
    typeof v.season === 'string' &&
    typeof v.paper === 'string'
  );
}

export function parseStoredBasket(raw: string | null): StoredBasket | null {
  if (!raw) return null;
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== 'object' || data === null) return null;
  const d = data as Record<string, unknown>;
  if (typeof d.subjectId !== 'string' || typeof d.title !== 'string' || !Array.isArray(d.items)) {
    return null;
  }
  return { subjectId: d.subjectId, title: d.title, items: d.items.filter(isQuestionItem) };
}
