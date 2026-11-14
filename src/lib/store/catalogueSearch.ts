/**
 * Text search over the shop catalogue, run in the browser.
 *
 * Every word typed must appear somewhere in the book's title, subtitle, code,
 * summary, level or kind. Students type short unit names ("m1", "p3") as often
 * as subject names, so a few of those are expanded to the words the titles use.
 */

export interface SearchableBook {
  title: string
  subtitle: string | null
  subjectCode: string | null
  spec: string | null
  level: string
  kind: "yearwise" | "workbook"
}

const KIND_WORDS: Record<SearchableBook["kind"], string> = {
  yearwise: "yearwise year wise booklet booklets question papers",
  workbook: "chapterwise chapter wise topicwise topic workbook workbooks",
}

/** Unit shorthand -> the Pearson unit code it stands for. */
const UNIT_ALIASES: Readonly<Record<string, string>> = {
  m1: "wme01", m2: "wme02", m3: "wme03",
  s1: "wst01", s2: "wst02",
  p1: "wma11", p2: "wma12", p3: "wma13", p4: "wma14",
  fpm: "4pm1",
}

function normalise(text: string): string {
  return text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, " ").trim()
}

function haystack(book: SearchableBook): string {
  return normalise([
    book.title, book.subtitle ?? "", book.subjectCode ?? "", book.spec ?? "",
    book.level, book.level === "IAL" ? "international a level" : "",
    KIND_WORDS[book.kind], "book books",
  ].join(" "))
}

/** Books matching every word of the query, in their original order. */
export function searchCatalogue<T extends SearchableBook>(books: readonly T[], query: string): T[] {
  const words = normalise(query).split(" ").filter(Boolean)
  if (words.length === 0) return [...books]
  return books.filter(book => {
    const text = haystack(book)
    const tokens = new Set(text.split(" "))
    return words.every(word => {
      const alias = UNIT_ALIASES[word]
      // A shorthand such as "m1" must match as a whole word or through its
      // unit code; as a bare substring it would also hit "4pm1".
      if (alias) return tokens.has(word) || text.includes(alias)
      return text.includes(word)
    })
  })
}
