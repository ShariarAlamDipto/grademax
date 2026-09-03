import { ADS_TXT } from '@/lib/ads'

// Prerendered at build time, so /ads.txt is served as a static file — it is a
// route rather than a file in public/ only so that it derives its publisher ID
// from the same constant the <head> snippet uses and the two cannot drift.
export const dynamic = 'force-static'

export function GET(): Response {
  return new Response(`${ADS_TXT}\n`, {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  })
}
