import type { Metadata } from "next"
import { publicPageMetadata } from "@/lib/metadata"
import Link from "next/link"
import Image from "next/image"
import { listActiveProducts } from "@/lib/store/catalogue"
import { getSettings } from "@/lib/store/settings"
import { formatBdt } from "@/lib/store/format"
import { Badge, Button, PageHeader, card } from "@/components/store/StoreUI"

export const metadata: Metadata = publicPageMetadata({
  path: '/store',
  title: "Shop Edexcel IGCSE & IAL Books in Bangladesh",
  description:
    "Shop Edexcel IGCSE and IAL workbooks and yearwise question booklets. Preview the books online and order spiral-bound copies delivered across Bangladesh.",
})

// Prices and stock change from the admin portal, so this must not be cached.
export const dynamic = "force-dynamic"

export default async function StorePage() {
  const [products, settings] = await Promise.all([listActiveProducts(), getSettings()])

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

  return (
    <main style={{ maxWidth: "72rem", margin: "0 auto", padding: "3rem 1.25rem 4rem" }}>
      <PageHeader
        title="Books and Workbooks"
        lead="Printed Edexcel IGCSE and IAL workbooks and yearwise exam-paper collections, delivered across Bangladesh. Check each edition and read a sample before you order."
        action={<Button href="/store/orders" variant="ghost">Track an order</Button>}
      />

      <p style={{ color: "var(--gm-text-2)", fontSize: "0.9rem", lineHeight: 1.7, marginBottom: "1.5rem" }}>
        Choosing between chapterwise and yearwise practice? Read our{" "}
        <Link href="/books/bangladesh" className="gm-link">guide to Edexcel books in Bangladesh</Link>{" "}
        for syllabus checks, delivery charges and payment options.
      </p>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 20rem), 1fr))",
        gap: "1.1rem",
      }}>
        {products.map(product => {
          const print = product.variants.find(v => v.kind === "print")
          const digital = product.variants.find(v => v.kind === "digital")
          const cheapest = Math.min(...product.variants.map(v => v.price_bdt))
          const soldOut = print ? !print.in_stock : false

          return (
            <Link
              key={product.id}
              href={`/store/${product.slug}`}
              style={{ ...card, display: "flex", flexDirection: "column", gap: "0.7rem", textDecoration: "none", color: "inherit" }}
            >
              {/* The cover leads the card: a buyer recognises the book before
                  they read its title. A2-ratio box so a missing cover cannot
                  make one card taller than its neighbours. */}
              <div style={{
                position: "relative",
                aspectRatio: "210 / 297",
                borderRadius: "0.5rem",
                overflow: "hidden",
                background: "var(--gm-surface-2)",
                border: "1px solid var(--gm-border)",
              }}>
                {product.cover_image_url ? (
                  <Image
                    src={product.cover_image_url}
                    alt={`Front cover of ${product.title}`}
                    fill
                    sizes="(max-width: 640px) 100vw, 20rem"
                    style={{ objectFit: "cover" }}
                  />
                ) : (
                  <span style={{
                    position: "absolute", inset: 0, display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: "0.75rem", color: "var(--gm-text-3)",
                  }}>
                    Cover coming soon
                  </span>
                )}
              </div>

              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                {product.subject_code ? <Badge tone="blue">{product.subject_code}</Badge> : null}
                {product.preview_url ? <Badge tone="amber">Preview</Badge> : null}
                {digital ? <Badge tone="green">Instant PDF</Badge> : null}
                {soldOut ? <Badge tone="red">Out of stock</Badge> : null}
              </div>

              <div>
                <h2 style={{ fontSize: "1.05rem", fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.35 }}>
                  {product.title}
                </h2>
                {product.subtitle ? (
                  <p style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", marginTop: "0.2rem" }}>
                    {product.subtitle}
                  </p>
                ) : null}
              </div>

              {product.spec_summary ? (
                <p style={{ fontSize: "0.8rem", color: "var(--gm-text-2)" }}>{product.spec_summary}</p>
              ) : null}

              <div style={{ marginTop: "auto", paddingTop: "0.6rem", borderTop: "1px solid var(--gm-border)" }}>
                <span style={{ fontSize: "0.7rem", color: "var(--gm-text-3)", display: "block" }}>
                  {product.variants.length > 1 ? "From" : "Price"}
                </span>
                <strong style={{ fontSize: "1.25rem", fontWeight: 800 }}>{formatBdt(cheapest)}</strong>
                {print && digital ? (
                  <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)", marginLeft: "0.5rem" }}>
                    print or PDF
                  </span>
                ) : null}
              </div>
            </Link>
          )
        })}
      </div>

      <section style={{ ...card, marginTop: "2rem" }}>
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
    </main>
  )
}
