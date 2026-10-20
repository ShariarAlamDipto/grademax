import type { Metadata } from "next"
import { publicPageMetadata, SITE_URL } from "@/lib/metadata"
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
  if (!product) notFound()
  return publicPageMetadata({
    path: `/store/${product.slug}`,
    title: product.title,
    description: ([product.subtitle, product.spec_summary].filter(Boolean).join('. ')
      || product.description
      || `Preview ${product.title} and order a copy from GradeMax.`)
      + (product.variants.some(variant => variant.kind === 'print') ? ' Printed copies delivered across Bangladesh. Prices in BDT.' : ''),
    image: product.cover_image_url,
  })
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const [product, settings] = await Promise.all([getProductBySlug(slug), getSettings()])

  if (!product || !settings.storeEnabled) notFound()

  const others = (await listActiveProducts()).filter(p => p.slug !== product.slug).slice(0, 3)
  const url = `${SITE_URL}/store/${product.slug}`
  const productSchema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    '@id': `${url}#product`,
    name: product.title,
    description: product.description || product.subtitle || product.title,
    url,
    ...(product.cover_image_url ? { image: [product.cover_image_url] } : {}),
    brand: { '@type': 'Brand', name: 'GradeMax' },
    offers: product.variants.map(variant => ({
      '@type': 'Offer',
      name: variant.label,
      sku: variant.id,
      url,
      priceCurrency: 'BDT',
      price: variant.price_bdt,
      availability: variant.in_stock ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
      ...(variant.kind === 'print' ? { eligibleRegion: { '@type': 'Country', name: 'Bangladesh', identifier: 'BD' } } : {}),
      seller: { '@id': `${SITE_URL}/#organization` },
    })),
  }
  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
      { '@type': 'ListItem', position: 2, name: 'Books', item: `${SITE_URL}/store` },
      { '@type': 'ListItem', position: 3, name: product.title, item: url },
    ],
  }

  return (
    <main style={{ maxWidth: "72rem", margin: "0 auto", padding: "2.5rem 1.25rem 4rem" }}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productSchema).replace(/</g, '\\u003c') }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema).replace(/</g, '\\u003c') }}
      />
      <nav aria-label="Breadcrumb" style={{ fontSize: "0.8rem", color: "var(--gm-text-3)", marginBottom: "1.25rem" }}>
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

      {product.variants.some(variant => variant.kind === 'print') ? (
        <p style={{ color: "var(--gm-text-2)", lineHeight: 1.7, fontSize: "0.85rem", marginTop: "1.5rem" }}>
          Ordering a printed copy? Read the{" "}
          <Link href="/books/bangladesh#delivery" className="gm-link">Bangladesh delivery and payment guide</Link>{" "}
          or <Link href="/books/bangladesh#choose-format" className="gm-link">compare chapterwise and yearwise practice</Link> before choosing your edition.
        </p>
      ) : null}

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
