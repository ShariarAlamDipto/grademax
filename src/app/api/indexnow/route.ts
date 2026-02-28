import { NextRequest, NextResponse } from 'next/server'

const INDEXNOW_KEY = 'fa3b4d74ad7b4a9eaf4232630b44aeaa'
const SITE_URL = 'https://grademax.me'

// IndexNow endpoints for different search engines
const INDEXNOW_ENDPOINTS = [
  'https://api.indexnow.org/indexnow',
  'https://www.bing.com/indexnow',
  'https://yandex.com/indexnow',
]

export async function POST(request: NextRequest) {
  try {
    const { urls } = await request.json()
    
    if (!urls || !Array.isArray(urls) || urls.length === 0) {
      return NextResponse.json({ error: 'No URLs provided' }, { status: 400 })
    }

    // Prepare the IndexNow payload
    const payload = {
      host: 'grademax.me',
      key: INDEXNOW_KEY,
      keyLocation: `${SITE_URL}/${INDEXNOW_KEY}.txt`,
      urlList: urls.map(url => url.startsWith('http') ? url : `${SITE_URL}${url}`)
    }

    // Submit to all IndexNow endpoints
    const results = await Promise.allSettled(
      INDEXNOW_ENDPOINTS.map(async (endpoint) => {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        return { endpoint, status: response.status, ok: response.ok }
      })
    )

    return NextResponse.json({
      success: true,
      message: 'URLs submitted to IndexNow',
      results: results.map((r, i) => ({
        engine: INDEXNOW_ENDPOINTS[i],
        ...(r.status === 'fulfilled' ? r.value : { error: r.reason })
      }))
    })

  } catch (error) {
    console.error('IndexNow error:', error)
    return NextResponse.json({ error: 'Failed to submit URLs' }, { status: 500 })
  }
}

// GET endpoint to submit all site pages at once
export async function GET() {
  const allUrls = [
    '/',
    '/generate',
    '/browse',
    '/past-papers',
    '/about',
    '/contact',
    '/privacy',
    '/terms',
  ]

  const payload = {
    host: 'grademax.me',
    key: INDEXNOW_KEY,
    keyLocation: `${SITE_URL}/${INDEXNOW_KEY}.txt`,
    urlList: allUrls.map(url => `${SITE_URL}${url}`)
  }

  try {
    const results = await Promise.allSettled(
      INDEXNOW_ENDPOINTS.map(async (endpoint) => {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        return { endpoint, status: response.status, ok: response.ok }
      })
    )

    return NextResponse.json({
      success: true,
      message: 'All pages submitted to IndexNow',
      urls: allUrls,
      results: results.map((r, i) => ({
        engine: INDEXNOW_ENDPOINTS[i],
        ...(r.status === 'fulfilled' ? r.value : { error: r.reason })
      }))
    })
  } catch (error) {
    console.error('IndexNow error:', error)
    return NextResponse.json({ error: 'Failed to submit URLs' }, { status: 500 })
  }
}
