import type { Metadata } from "next"
import { notFound } from "next/navigation"
import Link from "next/link"
import Image from "next/image"
import { getProductBySlug, listActiveProducts } from "@/lib/store/catalogue"
import { getSettings } from "@/lib/store/settings"
import ProductBuyPanel from "@/components/store/ProductBuyPanel"
import { PageHeader, card } from "@/components/store/StoreUI"

export const dynamic = "force-dynamic"

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params
  const product = await getProductBySlug(slug)
  if (!product) return { title: "Not found" }
  return {
    title: product.title,
    description: product.subtitle ?? product.spec_summary ?? undefined,
  }
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const [product, settings] = await Promise.all([getProductBySlug(slug), getSettings()])

  if (!product || !settings.storeEnabled) notFound()

  const others = (await listActiveProducts()).filter(p => p.slug !== product.slug).slice(0, 3)

  return (
    <main style={{ maxWidth: "72rem", margin: "0 auto", padding: "2.5rem 1.25rem 4rem" }}>
      <nav style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", marginBottom: "1.25rem" }}>
        <Link href="/store" className="gm-link">Books</Link>
        <span style={{ margin: "0 0.4rem" }}>/</span>
        <span>{product.title}</span>
      </nav>

      <PageHeader title={product.title} lead={product.subtitle ?? undefined} />

      <div style={{ display: "grid", gap: "1.5rem", alignItems: "start" }}
           className="gm-store-product-grid">
        <div>
          {/* The cover, at the size a buyer would hold it. Capped in height so
              a tall A4 render cannot push the buy panel below the fold. */}
          {product.cover_image_url ? (
            <div style={{
              position: "relative",
              aspectRatio: "210 / 297",
              maxHeight: "26rem",
              marginBottom: "1.1rem",
              borderRadius: "0.6rem",
              overflow: "hidden",
              border: "1px solid var(--gm-border)",
              background: "var(--gm-surface-2)",
            }}>
              <Image
                src={product.cover_image_url}
                alt={`Front cover of ${product.title}`}
                fill
                sizes="(max-width: 640px) 100vw, 26rem"
                style={{ objectFit: "contain" }}
                priority
              />
            </div>
          ) : null}

          {product.description ? (
            <div style={{ ...card, marginBottom: "1.1rem" }}>
              <p style={{ fontSize: "0.92rem", lineHeight: 1.7, color: "var(--gm-text-2)" }}>
                {product.description}
              </p>
              {product.spec_summary ? (
                <p style={{ fontSize: "0.82rem", color: "var(--gm-text-3)", marginTop: "0.8rem", paddingTop: "0.8rem", borderTop: "1px solid var(--gm-border)" }}>
                  {product.spec_summary}
                </p>
              ) : null}
            </div>
          ) : null}

          <ProductBuyPanel product={product} settings={{
            slaHours: settings.verificationSlaHours,
            deliveryMetro: settings.deliveryBdtMetro,
            deliveryOutside: settings.deliveryBdtOutside,
          }} showPreviewOnly />
        </div>

        <ProductBuyPanel product={product} settings={{
          slaHours: settings.verificationSlaHours,
          deliveryMetro: settings.deliveryBdtMetro,
          deliveryOutside: settings.deliveryBdtOutside,
        }} />
      </div>

      {others.length > 0 ? (
        <section style={{ marginTop: "2.5rem" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.9rem" }}>Other books</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 16rem), 1fr))", gap: "0.9rem" }}>
            {others.map(p => (
              <Link key={p.id} href={`/store/${p.slug}`} style={{ ...card, textDecoration: "none", color: "inherit", padding: "0.9rem" }}>
                <strong style={{ fontSize: "0.9rem", fontWeight: 700, display: "block", lineHeight: 1.35 }}>{p.title}</strong>
                {p.subtitle ? (
                  <span style={{ fontSize: "0.75rem", color: "var(--gm-text-3)" }}>{p.subtitle}</span>
                ) : null}
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  )
}
