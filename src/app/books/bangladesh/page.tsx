import type { Metadata } from 'next'
import type { CSSProperties } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { publicPageMetadata, SITE_URL } from '@/lib/metadata'
import { listActiveProducts } from '@/lib/store/catalogue'
import { formatBdt } from '@/lib/store/format'
import { getSettings } from '@/lib/store/settings'

const pageMetadata = publicPageMetadata({
  path: '/books/bangladesh',
  title: 'Edexcel Books & Workbooks in Bangladesh',
  description: 'Compare GradeMax Edexcel IGCSE and IAL printed workbooks and yearwise books. Preview editions, check prices in BDT and see Bangladesh delivery options.',
})

export const metadata: Metadata = {
  ...pageMetadata,
  openGraph: { ...pageMetadata.openGraph, locale: 'en_BD' },
}

// Match the shop: never publish a cached price, stock level or delivery charge.
export const dynamic = 'force-dynamic'

const panel: CSSProperties = {
  background: 'var(--gm-surface)',
  border: '1px solid var(--gm-border)',
  borderRadius: '0.85rem',
  padding: '1.4rem',
}
const heading: CSSProperties = {
  fontSize: 'clamp(1.2rem, 3vw, 1.65rem)', fontWeight: 800,
  lineHeight: 1.2, letterSpacing: '-0.025em', marginBottom: '0.8rem',
}
const prose: CSSProperties = { color: 'var(--gm-text-2)', lineHeight: 1.75, fontSize: '0.95rem' }

export default async function BangladeshBooksPage() {
  const [settings, products] = await Promise.all([getSettings(), listActiveProducts()])
  const printedBooks = settings.storeEnabled
    ? products.filter(product => product.variants.some(variant => variant.kind === 'print'))
    : []
  const wallets = [settings.bkashNumber.trim() && 'bKash', settings.nagadNumber.trim() && 'Nagad'].filter(Boolean)
  const url = `${SITE_URL}/books/bangladesh`
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        '@id': `${url}#webpage`,
        url,
        name: 'Edexcel Books & Workbooks in Bangladesh',
        description: pageMetadata.description,
        isPartOf: { '@id': `${SITE_URL}/#website` },
        inLanguage: 'en-BD',
        spatialCoverage: { '@type': 'Country', name: 'Bangladesh', identifier: 'BD' },
        breadcrumb: { '@id': `${url}#breadcrumb` },
        ...(printedBooks.length ? { mainEntity: { '@id': `${url}#books` } } : {}),
      },
      {
        '@type': 'BreadcrumbList',
        '@id': `${url}#breadcrumb`,
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: SITE_URL },
          { '@type': 'ListItem', position: 2, name: 'Books', item: `${SITE_URL}/store` },
          { '@type': 'ListItem', position: 3, name: 'Books in Bangladesh', item: url },
        ],
      },
      ...(printedBooks.length ? [{
        '@type': 'ItemList',
        '@id': `${url}#books`,
        name: 'Printed GradeMax books available in the catalogue',
        numberOfItems: printedBooks.length,
        itemListElement: printedBooks.map((product, index) => ({
          '@type': 'ListItem', position: index + 1,
          name: product.title, url: `${SITE_URL}/store/${product.slug}`,
        })),
      }] : []),
    ],
  }

  return (
    <main style={{ maxWidth: '72rem', margin: '0 auto', padding: '2.5rem 1.25rem 4rem', color: 'var(--gm-text)' }}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema).replace(/</g, '\\u003c') }} />
      <nav aria-label="Breadcrumb" style={{ fontSize: '0.8rem', marginBottom: '1.5rem', color: 'var(--gm-text-3)' }}>
        <Link href="/" className="gm-link">Home</Link> / <Link href="/store" className="gm-link">Books</Link> / Bangladesh
      </nav>

      <header style={{ maxWidth: '48rem', marginBottom: '2.5rem' }}>
        <p style={{ color: 'var(--gm-amber)', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
          GradeMax books · Bangladesh
        </p>
        <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.3rem)', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1, marginBottom: '1rem' }}>
          Edexcel books and workbooks, delivered in Bangladesh.
        </h1>
        <p style={prose}>
          Choose printed practice for Edexcel International GCSE (IGCSE) and International A Level (IAL).
          GradeMax brings workbooks and yearwise exam-paper collections into one shop, with prices in
          Bangladeshi taka and delivery across Bangladesh. Check the edition, syllabus code and sample
          pages before choosing the book for your revision.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>
          <Link href="#printed-books" className="btn-beacon">Compare printed books</Link>
          <Link href="#delivery" className="btn-ghost-amber">Delivery and payment</Link>
        </div>
      </header>

      <section aria-labelledby="choose-format" style={{ marginBottom: '2.5rem' }}>
        <h2 id="choose-format" style={heading}>Chapterwise workbook or yearwise book?</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))', gap: '1rem' }}>
          <div style={panel}>
            <h3 style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Use a workbook for focused practice</h3>
            <p style={prose}>
              A chapterwise workbook groups questions by topic. Use it when you have finished a chapter
              in class, want more practice on a difficult method, or need to work through one part of
              the syllabus before returning to complete papers. Look inside the book to check its topic
              order and answer space.
            </p>
          </div>
          <div style={panel}>
            <h3 style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Use a yearwise book for exam practice</h3>
            <p style={prose}>
              A yearwise collection keeps exam papers together by year and session. Choose it for
              timed practice and moving between topics as you would in an exam. Check which years,
              sessions and paper variants each edition includes, and whether the sample shows the
              mark schemes or solutions you need.
            </p>
          </div>
        </div>
      </section>

      <section id="printed-books" aria-labelledby="printed-heading" style={{ marginBottom: '2.5rem', scrollMarginTop: '6rem' }}>
        <h2 id="printed-heading" style={heading}>Printed books and current prices</h2>
        <p style={{ ...prose, marginBottom: '1rem' }}>
          These are the printed editions in the current GradeMax catalogue. Open a title to see its
          full description and available sample pages. Stock and prices are checked when you order.
        </p>
        {printedBooks.length ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 20rem), 1fr))', gap: '1rem' }}>
            {printedBooks.map(product => {
              const print = product.variants.find(variant => variant.kind === 'print')!
              return (
                <Link key={product.id} href={`/store/${product.slug}`} className="gm-link" style={{ ...panel, display: 'flex', flexDirection: 'column', color: 'inherit', textDecoration: 'none' }}>
                  {product.cover_image_url ? (
                    <div style={{ position: 'relative', height: '13rem', marginBottom: '1rem', background: 'var(--gm-surface-2)', borderRadius: '0.5rem', overflow: 'hidden' }}>
                      <Image src={product.cover_image_url} alt={`Front cover of ${product.title}`} fill sizes="(max-width: 640px) 90vw, 20rem" style={{ objectFit: 'contain' }} />
                    </div>
                  ) : null}
                  <h3 style={{ fontSize: '1rem', fontWeight: 750, lineHeight: 1.4 }}>{product.title}</h3>
                  {product.subtitle ? <p style={{ ...prose, fontSize: '0.85rem', marginTop: '0.35rem' }}>{product.subtitle}</p> : null}
                  {product.spec_summary ? <p style={{ ...prose, fontSize: '0.8rem', marginTop: '0.5rem' }}>{product.spec_summary}</p> : null}
                  <div style={{ marginTop: 'auto', paddingTop: '1rem', display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <strong>{formatBdt(print.price_bdt)} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>print</span></strong>
                    <span style={{ color: print.in_stock ? 'var(--gm-green)' : 'var(--gm-text-3)', fontSize: '0.8rem' }}>{print.in_stock ? 'In stock' : 'Out of stock'}</span>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--gm-amber)', marginTop: '0.7rem' }}>View edition and sample →</span>
                </Link>
              )
            })}
          </div>
        ) : (
          <div style={panel}>
            <p style={prose}>Printed books are not available to order right now. You can still use the <Link href="/past-papers" className="gm-link">free past-paper library</Link> while the next editions are prepared.</p>
          </div>
        )}
      </section>

      <section aria-labelledby="syllabus-heading" style={{ ...panel, marginBottom: '2.5rem' }}>
        <h2 id="syllabus-heading" style={heading}>Match the book to your syllabus</h2>
        <p style={{ ...prose, marginBottom: '1rem' }}>
          Check the subject code with your school or teacher before ordering. Maths A and Maths B
          are different International GCSE specifications. IAL Pure Mathematics units are also
          different from International GCSE Further Pure Mathematics. A similar title does not mean
          the book covers your exam.
        </p>
        <ul style={{ ...prose, paddingLeft: '1.2rem', display: 'grid', gap: '0.5rem' }}>
          <li><Link href="/subjects/igcse/maths-b" className="gm-link">IGCSE Mathematics B</Link>: check for 4MB1.</li>
          <li><Link href="/subjects/ial/mechanics-1" className="gm-link">IAL Mechanics 1 (M1)</Link>: check for WME01.</li>
          <li><Link href="/subjects/ial/statistics-1" className="gm-link">IAL Statistics 1 (S1)</Link>: check for WST01.</li>
          <li>IAL Pure Mathematics: <Link href="/subjects/ial/pure-mathematics-1" className="gm-link">P1 (WMA11)</Link>, <Link href="/subjects/ial/pure-mathematics-2" className="gm-link">P2 (WMA12)</Link>, <Link href="/subjects/ial/pure-mathematics-3" className="gm-link">P3 (WMA13)</Link> and <Link href="/subjects/ial/pure-mathematics-4" className="gm-link">P4 (WMA14)</Link> are separate units.</li>
        </ul>
        <p style={{ ...prose, fontSize: '0.85rem', marginTop: '1rem' }}>
          GradeMax is an independent study resource and is not affiliated with or endorsed by Pearson Edexcel.
        </p>
      </section>

      <section id="delivery" aria-labelledby="delivery-heading" style={{ marginBottom: '2.5rem', scrollMarginTop: '6rem' }}>
        <h2 id="delivery-heading" style={heading}>Ordering from Bangladesh</h2>
        {settings.storeEnabled ? (
          <div style={panel}>
            <dl style={{ display: 'grid', gap: '1.2rem' }}>
              <div>
                <dt style={{ fontWeight: 700, marginBottom: '0.3rem' }}>Delivery charges</dt>
                <dd style={prose}>Inside Dhaka: {formatBdt(settings.deliveryBdtMetro)}. Elsewhere in Bangladesh: {formatBdt(settings.deliveryBdtOutside)}. Delivery is charged once per order, rather than once per book. Choose your district at checkout to see the total.</dd>
                {settings.freeDeliveryOverBdt > 0 ? <dd style={prose}>Free delivery applies when the order subtotal reaches {formatBdt(settings.freeDeliveryOverBdt)}.</dd> : null}
              </div>
              <div>
                <dt style={{ fontWeight: 700, marginBottom: '0.3rem' }}>Payment</dt>
                <dd style={prose}>Printed-only orders can use cash on delivery.{wallets.length ? ` Advance payment is also available through ${wallets.join(' or ')}. Use the payment details shown at checkout.` : ''} Your checkout shows the payment methods available for your order.</dd>
              </div>
              <div>
                <dt style={{ fontWeight: 700, marginBottom: '0.3rem' }}>Order details and tracking</dt>
                <dd style={prose}>{settings.requireAccount ? 'Sign in to place your order. ' : ''}Enter your delivery address, district and contact number at checkout. You can <Link href="/store/orders" className="gm-link">track your order</Link> after placing it. For a question about an edition or delivery, <Link href="/contact" className="gm-link">contact GradeMax</Link> before ordering.</dd>
              </div>
            </dl>
          </div>
        ) : <p style={prose}>The shop is currently closed for orders. Delivery and payment details will be shown here when ordering reopens.</p>}
      </section>

      <section aria-labelledby="free-heading" style={panel}>
        <h2 id="free-heading" style={heading}>Start practising before your book arrives</h2>
        <p style={prose}>
          Browse the <Link href="/edexcel-igcse-past-papers" className="gm-link">free Edexcel IGCSE papers</Link> or <Link href="/edexcel-a-level-past-papers" className="gm-link">IAL papers and mark schemes</Link>.
          Use a complete paper to spot weaker topics, then revisit those topics in your workbook.
          When you are ready for timed practice, return to a fresh paper in your yearwise collection.
          Our <Link href="/edexcel-worksheets" className="gm-link">worksheet guide</Link> explains the subjects supported by the online practice tools.
        </p>
      </section>
    </main>
  )
}
