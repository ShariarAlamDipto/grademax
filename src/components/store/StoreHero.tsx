import Link from "next/link"
import { BookWheel, type WheelBook } from "@/components/store/BookWheel"
import "./store-refresh.css"

/**
 * The shop's opening section: the page title, then the book wheel (every book,
 * turned by the visitor's scroll or swipe) directly on the page.
 */

interface StoreHeroProps {
  books: WheelBook[]
}

export function StoreHero({ books }: StoreHeroProps) {
  return (
    <section className="sh-hero" aria-labelledby="store-title">
      <p className="sh-eyebrow">GradeMax print shop · Bangladesh</p>
      <h1 id="store-title" className="sh-title">Books and Workbooks</h1>
      <p className="sh-lead">
        Printed Edexcel IGCSE and IAL workbooks and yearwise exam-paper collections, delivered across
        Bangladesh. Check each edition and read a sample before you order.
      </p>
      <div className="sh-actions">
        <Link href="/store/orders" className="sh-pill">Track an order</Link>
        <Link href="/books/bangladesh" className="sh-pill">Which book do I need?</Link>
      </div>

      {books.length > 0 ? (
        <div className="sh-stage">
          <BookWheel books={books} />
        </div>
      ) : null}
    </section>
  )
}
