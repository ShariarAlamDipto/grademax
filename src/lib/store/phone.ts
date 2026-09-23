/**
 * Bangladesh mobile number handling.
 *
 * Buyers type their number every way imaginable: +8801712345678, 8801712345678,
 * 01712-345678, 01712 345678. All of those are the same person, and the order
 * lookup matches on this field, so they must all normalise to one form:
 * eleven digits beginning 01.
 *
 * Operator prefixes in use are 013 (Grameenphone), 014 (Banglalink),
 * 015 (Teletalk), 016 (Airtel), 017 (Grameenphone), 018 (Robi), 019 (Banglalink).
 */

const BD_MOBILE = /^01[3-9]\d{8}$/

/**
 * Reduce any accepted spelling to `01XXXXXXXXX`, or return null if it is not a
 * Bangladeshi mobile number. Returning null rather than throwing lets callers
 * decide whether a bad number is a 400 or a field-level form error.
 */
export function normalizeBdPhone(input: string | null | undefined): string | null {
  if (!input) return null

  // Strip everything that is not a digit or a leading plus.
  let s = String(input).trim().replace(/[\s\-().]/g, "")
  if (s.startsWith("+")) s = s.slice(1)
  if (!/^\d+$/.test(s)) return null

  // 8801712345678 -> 01712345678
  if (s.startsWith("880")) s = `0${s.slice(3)}`
  // 1712345678 -> 01712345678 (the leading zero is commonly dropped)
  else if (s.length === 10 && s.startsWith("1")) s = `0${s}`

  return BD_MOBILE.test(s) ? s : null
}

export function isValidBdPhone(input: string | null | undefined): boolean {
  return normalizeBdPhone(input) !== null
}

/**
 * Compare a number the buyer typed against a stored one, tolerating format
 * differences. Used by the guest order lookup.
 */
export function phoneMatches(a: string | null | undefined, b: string | null | undefined): boolean {
  const na = normalizeBdPhone(a)
  const nb = normalizeBdPhone(b)
  return na !== null && nb !== null && na === nb
}
