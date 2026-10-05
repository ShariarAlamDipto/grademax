/**
 * The page numbers to show as buttons: at most `maxButtons`, centred on the
 * current page and pinned to the first/last page near either end.
 */
export function pageWindow(current: number, totalPages: number, maxButtons: number): number[] {
  const count = Math.min(totalPages, maxButtons);
  if (count <= 0) return [];

  const half = Math.floor(count / 2);
  const start = Math.min(Math.max(1, current - half), totalPages - count + 1);
  return Array.from({ length: count }, (_, i) => start + i);
}
