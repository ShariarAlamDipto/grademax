"use client"

/** localStorage key; the pre-paint script in layout.tsx reads the same key. */
export const PROMO_DISMISS_KEY = "gm-promo-dismissed"

/**
 * Hides the promo banner for good on this browser. The `gm-promo-off` class on
 * <html> is what actually hides it (see globals.css), so the pre-paint script
 * can apply the same class on later visits without a flash.
 */
export default function PromoBannerClose() {
  function dismiss() {
    document.documentElement.classList.add("gm-promo-off")
    try {
      localStorage.setItem(PROMO_DISMISS_KEY, "1")
    } catch {
      // Storage blocked (private mode etc.) — it stays hidden for this page view only.
    }
  }

  return (
    <button type="button" className="gm-promo-close" onClick={dismiss} aria-label="Dismiss announcement">
      ×
    </button>
  )
}
