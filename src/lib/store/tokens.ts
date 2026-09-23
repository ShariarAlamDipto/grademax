/**
 * Order numbers.
 *
 * An order number is shown to the buyer and used, with their phone number, to
 * look the order up without signing in. A bare sequence (GM-1001, GM-1002)
 * would let anyone walk the lookup endpoint, so a short random suffix is
 * appended. The sequential part still comes from a Postgres SEQUENCE, because
 * SELECT max()+1 collides under concurrency.
 *
 * Download access is NOT handled here — it is a short-lived signed grant, in
 * `downloadGrant.ts`. There is deliberately no stored download token: a
 * permanent credential in a URL gets forwarded, and it could not be shown on
 * the tracking page anyway.
 */
import { randomBytes } from "node:crypto"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"

/** Crockford base32 without I, L, O, U — no ambiguity when read aloud. */
const ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

function randomCode(length: number): string {
  const bytes = randomBytes(length)
  let out = ""
  for (let i = 0; i < length; i++) out += ALPHABET[bytes[i]! % ALPHABET.length]
  return out
}

/**
 * "GM-1042-K7QX". Sequential enough to be human-sortable for the owner,
 * random enough not to be enumerable by a stranger.
 */
export async function generateOrderNumber(): Promise<string> {
  const db = getSupabaseAdmin()
  let seq = 0
  if (db) {
    const { data } = await db.rpc("store_next_order_seq")
    seq = typeof data === "number" ? data : 0
  }
  // A fallback that is still unique enough to satisfy the UNIQUE constraint if
  // the sequence is unreachable; the random suffix carries the collision load.
  if (!seq) seq = Math.floor(Date.now() / 1000) % 100000
  return `GM-${seq}-${randomCode(4)}`
}
