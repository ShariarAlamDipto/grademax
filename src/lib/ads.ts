// Google AdSense wiring.
//
// The publisher ID is public by design — it ships in every page's <head> and
// again in /ads.txt — so it is a plain constant here rather than an env var.
// It lives in exactly one place because its two consumers have to agree: if the
// <head> snippet and ads.txt name different publishers, AdSense stops serving
// and the site fails review.

export const ADSENSE_CLIENT_ID = 'ca-pub-9054237287762899'

// The loader from the AdSense console. Rendered server-side into <head> (see
// app/layout.tsx) rather than through next/script, so it is present in the raw
// HTML that AdSense's site-review crawler reads — a tag injected later by
// client JavaScript can be missed entirely.
export const ADSENSE_SCRIPT_SRC =
  `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT_ID}`

// ads.txt authorises Google to sell this site's inventory; without it AdSense
// treats the inventory as unauthorised and demand drops. The publisher ID drops
// the "ca-" prefix in this file — that is the format's own quirk, not a typo.
// The trailing hash is Google's certification-authority ID, the same string for
// every AdSense publisher.
export const ADS_TXT = `google.com, ${ADSENSE_CLIENT_ID.replace(/^ca-/, '')}, DIRECT, f08c47fec0942fa0`
