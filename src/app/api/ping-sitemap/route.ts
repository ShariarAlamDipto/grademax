import { NextResponse } from 'next/server'

// Ping search engines to re-crawl the sitemap
const PING_URLS = [
  'https://www.google.com/ping?sitemap=https://grademax.me/sitemap.xml',
  'https://www.bing.com/ping?sitemap=https://grademax.me/sitemap.xml',
]

export async function GET() {
  try {
    const results = await Promise.allSettled(
      PING_URLS.map(async (url) => {
        const response = await fetch(url)
        return { url, status: response.status, ok: response.ok }
      })
    )

    return NextResponse.json({
      success: true,
      message: 'Sitemap ping sent to search engines',
      results: results.map((r, i) => ({
        engine: PING_URLS[i].includes('google') ? 'Google' : 'Bing',
        ...(r.status === 'fulfilled' ? r.value : { error: r.reason })
      }))
    })
  } catch (error) {
    console.error('Sitemap ping error:', error)
    return NextResponse.json({ error: 'Failed to ping search engines' }, { status: 500 })
  }
}
