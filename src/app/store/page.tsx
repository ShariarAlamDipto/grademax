import type { Metadata } from "next"
import { publicPageMetadata } from "@/lib/metadata"
import Link from "next/link"
import { listActiveProducts } from "@/lib/store/catalogue"
import { kindOf, levelOf, parseShelfFilter, shelve } from "@/lib/store/shelves"
import { getSettings } from "@/lib/store/settings"
import { formatBdt } from "@/lib/store/format"
import { PageHeader, card } from "@/components/store/StoreUI"
import { StoreHero } from "@/components/store/StoreHero"
import type { WheelBook } from "@/components/store/BookWheel"
import { StoreCatalogue, type CatalogueBook } from "@/components/store/StoreCatalogue"

export const metadata: Metadata = publicPageMetadata({
  path: '/store',
  title: "Shop Edexcel IGCSE & IAL Books in Bangladesh",
  description:
    "Shop Edexcel IGCSE and IAL workbooks and yearwise question booklets. Preview the books online and order spiral-bound copies delivered across Bangladesh.",
})

// Rendered per request (the shelf filter is a query string). The catalogue
// itself comes from the data cache, which admin edits and new orders clear;
// see src/lib/store/catalogueCache.ts.
export const dynamic = "force-dynamic"

interface StoreQuery {
  shelf?: string | string[]
}

export default async function StorePage({ searchParams }: { searchParams: Promise<StoreQuery> }) {
  const [products, settings, query] = await Promise.all([listActiveProducts(), getSettings(), searchParams])
  const filter = parseShelfFilter(query.shelf)

  if (!settings.storeEnabled || products.length === 0) {
    return (
      <main style={{ maxWidth: "62rem", margin: "0 auto", padding: "3rem 1.25rem" }}>
        <PageHeader
          title="Books and Workbooks"
          lead="The shop is not open yet. The printed workbooks are being prepared — check back shortly."
        />
        <div style={card}>
          <p style={{ color: "var(--gm-text-2)", fontSize: "0.9rem", lineHeight: 1.6 }}>
            In the meantime, every past paper on GradeMax is free to{" "}
            <Link href="/past-papers" className="gm-link">browse and download</Link>, and you can build your
            own practice sets with the <Link href="/test-builder" className="gm-link">Test Builder</Link>.
          </p>
        </div>
      </main>
    )
  }

  const books: CatalogueBook[] = products
    .filter(product => filter === "all" || shelve([product], filter).length > 0)
    .map(product => {
      const print = product.variants.find(v => v.kind === "print")
      const digital = product.variants.find(v => v.kind === "digital")
      return {
        id: product.id,
        slug: product.slug,
        title: product.title,
        subtitle: product.subtitle,
        subjectCode: product.subject_code,
        spec: product.spec_summary,
        coverUrl: product.cover_image_url,
        level: levelOf(product),
        kind: kindOf(product),
        priceLabel: formatBdt(Math.min(...product.variants.map(v => v.price_bdt))),
        priceFrom: product.variants.length > 1,
        hasPreview: Boolean(product.preview_url),
        hasDigital: Boolean(digital),
        printOrPdf: Boolean(print && digital),
        soldOut: print ? !print.in_stock : false,
      }
    })

  // The wheel carries every book that has a cover, whatever shelf is open below.
  const wheelBooks: WheelBook[] = products.flatMap(product =>
    product.cover_image_url
      ? [{
          slug: product.slug,
          title: product.title,
          coverUrl: product.cover_image_url,
          priceLabel: formatBdt(Math.min(...product.variants.map(v => v.price_bdt))),
        }]
      : [],
  )

  return (
    <main>
      <StoreHero books={wheelBooks} />
      <StoreCatalogue books={books} filter={filter} />

      <div style={{ maxWidth: "74rem", margin: "0 auto", padding: "0 1.25rem 4rem" }}>
      <section style={card}>
        <h2 style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.6rem" }}>Delivery and payment</h2>
        <ul style={{ fontSize: "0.85rem", color: "var(--gm-text-2)", lineHeight: 1.7, paddingLeft: "1.1rem" }}>
          <li>We deliver anywhere in Bangladesh — {formatBdt(settings.deliveryBdtMetro)} inside Dhaka, {formatBdt(settings.deliveryBdtOutside)} elsewhere. Delivery is charged once per order.</li>
          {settings.freeDeliveryOverBdt > 0 ? (
            <li>Free delivery when your order subtotal reaches {formatBdt(settings.freeDeliveryOverBdt)}.</li>
          ) : null}
          {/* Only promise a wallet that is actually configured — otherwise a
              buyer picks bKash and finds no number to send money to. */}
          <li>
            <strong>Cash on delivery</strong> is available for printed-only orders.
            {settings.bkashNumber.trim() || settings.nagadNumber.trim()
              ? ` You can also pay ahead with ${[settings.bkashNumber.trim() && "bKash", settings.nagadNumber.trim() && "Nagad"].filter(Boolean).join(" or ")}.`
              : null}
          </li>
          {settings.requireAccount ? <li>Sign in to order and track your delivery.</li> : <li>You can track your order after checkout.</li>}
          {settings.digitalSalesEnabled ? (
            <li>Digital downloads unlock as soon as your payment is confirmed, usually within {settings.verificationSlaHours} hours.</li>
          ) : null}
        </ul>
      </section>
      </div>
    </main>
  )
}
