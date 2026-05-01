import { NextRequest, NextResponse } from 'next/server'

const INDEXNOW_KEY = process.env.INDEXNOW_API_KEY || ''
const SITE_URL = 'https://grademax.me'

const INDEXNOW_ENDPOINTS = [
  'https://api.indexnow.org/indexnow',
  'https://www.bing.com/indexnow',
  'https://yandex.com/indexnow',
]

function isAuthorized(request: NextRequest): boolean {
  const cronSecret = process.env.CRON_SECRET
  if (!cronSecret) return false
  return request.headers.get('authorization') === `Bearer ${cronSecret}`
}

export async function POST(request: NextRequest) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const { urls } = await request.json()

    if (!urls || !Array.isArray(urls) || urls.length === 0) {
      return NextResponse.json({ error: 'No URLs provided' }, { status: 400 })
    }

    const payload = {
      host: 'grademax.me',
      key: INDEXNOW_KEY,
      keyLocation: `${SITE_URL}/${INDEXNOW_KEY}.txt`,
      urlList: urls.map(url => url.startsWith('http') ? url : `${SITE_URL}${url}`)
    }

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
        ...(r.status === 'fulfilled' ? r.value : { error: String(r.reason) })
      }))
    })

  } catch {
    return NextResponse.json({ error: 'Failed to submit URLs' }, { status: 500 })
  }
}

export async function GET(request: NextRequest) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

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
        ...(r.status === 'fulfilled' ? r.value : { error: String(r.reason) })
      }))
    })
  } catch {
    return NextResponse.json({ error: 'Failed to submit URLs' }, { status: 500 })
  }
}
