"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import Image from "next/image"
import { Badge } from "@/components/store/StoreUI"
import { SHELF_FILTERS, type Level, type ShelfFilter } from "@/lib/store/shelves"
import { searchCatalogue } from "@/lib/store/catalogueSearch"
import "./store-refresh.css"

/**
 * The searchable catalogue. The server sends every book on the chosen shelf;
 * typing narrows them in the browser, so a search costs no request. The shelf
 * filters stay plain links (each shelf keeps its own URL and works without
 * JavaScript).
 */

export interface CatalogueBook {
  id: string
  slug: string
  title: string
  subtitle: string | null
  subjectCode: string | null
  spec: string | null
  coverUrl: string | null
  level: Level
  kind: "yearwise" | "workbook"
  priceLabel: string
  priceFrom: boolean
  hasPreview: boolean
  hasDigital: boolean
  /** Sold both as a printed copy and as a PDF. */
  printOrPdf: boolean
  soldOut: boolean
}

interface StoreCatalogueProps {
  books: CatalogueBook[]
  filter: ShelfFilter
}

const SHELF_TITLE: Record<Level, string> = {
  IGCSE: "IGCSE",
  IAL: "International A Level (IAL)",
  Other: "More books",
}
const LEVELS: Level[] = ["IGCSE", "IAL", "Other"]

function countLabel(n: number): string {
  return `${n} ${n === 1 ? "book" : "books"}`
}

export function StoreCatalogue({ books, filter }: StoreCatalogueProps) {
  const [query, setQuery] = useState("")
  const found = useMemo(() => searchCatalogue(books, query), [books, query])
  const shelves = LEVELS
    .map(level => ({ level, items: found.filter(b => b.level === level) }))
    .filter(shelf => shelf.items.length > 0)
  const searching = query.trim().length > 0

  return (
    <div id="catalogue" className="sc-wrap">
      <div className="sc-search" role="search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <circle cx="11" cy="11" r="7" />
          <path strokeLinecap="round" d="M20 20l-3.5-3.5" />
        </svg>
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search books and booklets — subject, code or unit"
          aria-label="Search books and booklets"
          autoComplete="off"
        />
        {searching ? (
          <button type="button" className="sc-clear" onClick={() => setQuery("")} aria-label="Clear search">×</button>
        ) : null}
      </div>

      <nav aria-label="Filter books" className="sc-filters">
        {SHELF_FILTERS.map(f => (
          <Link
            key={f.key}
            href={f.key === "all" ? "/store#catalogue" : `/store?shelf=${f.key}#catalogue`}
            aria-current={f.key === filter ? "page" : undefined}
            className="sc-filter"
          >
            {f.label}
          </Link>
        ))}
      </nav>

      <p className="sc-count" aria-live="polite">
        {searching ? `${countLabel(found.length)} for “${query.trim()}”` : countLabel(books.length)}
      </p>

      {shelves.length === 0 ? (
        <div className="sc-empty">
          {searching ? (
            <>
              No book matches “{query.trim()}”. Try a subject name (Physics), a code (4MA1, WME01) or a unit (M1, P3).{" "}
              <button type="button" onClick={() => setQuery("")} className="gm-link" style={{ background: "none", border: 0, cursor: "pointer", font: "inherit", textDecoration: "underline" }}>
                Clear search
              </button>
            </>
          ) : (
            <>No books on this shelf yet. <Link href="/store" className="gm-link">See all books</Link>.</>
          )}
        </div>
      ) : null}

      {shelves.map((shelf, shelfIndex) => (
        <section key={shelf.level} className="sc-shelf" aria-labelledby={`shelf-${shelf.level}`}>
          <h2 id={`shelf-${shelf.level}`} className="sc-shelf-title">
            {SHELF_TITLE[shelf.level]}
            <span>{countLabel(shelf.items.length)}</span>
          </h2>
          <div className="sc-grid">
            {shelf.items.map((book, index) => (
              <Link key={book.id} href={`/store/${book.slug}`} className="sc-card">
                {/* The cover leads the card: a buyer recognises the book before
                    they read its title. A fixed-ratio box so a missing cover
                    cannot make one card taller than its neighbours. */}
                <div className="sc-cover">
                  {book.coverUrl ? (
                    <Image
                      src={book.coverUrl}
                      alt={`Front cover of ${book.title}`}
                      fill
                      sizes="(max-width: 640px) 100vw, 20rem"
                      style={{ objectFit: "cover" }}
                      priority={shelfIndex === 0 && index < 4}
                    />
                  ) : (
                    <span className="sc-nocover">Cover coming soon</span>
                  )}
                </div>

                <div className="sc-badges">
                  {book.subjectCode ? <Badge tone="blue">{book.subjectCode}</Badge> : null}
                  {book.hasPreview ? <Badge tone="amber">Preview</Badge> : null}
                  {book.hasDigital ? <Badge tone="green">Instant PDF</Badge> : null}
                  {book.soldOut ? <Badge tone="red">Out of stock</Badge> : null}
                </div>

                <div>
                  <h3 className="sc-name">{book.title}</h3>
                  {book.subtitle ? <p className="sc-sub">{book.subtitle}</p> : null}
                </div>

                {book.spec ? <p className="sc-spec">{book.spec}</p> : null}

                <div className="sc-price">
                  <small>{book.priceFrom ? "From" : "Price"}</small>
                  <strong>{book.priceLabel}</strong>
                  {book.printOrPdf ? <span>print or PDF</span> : null}
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
