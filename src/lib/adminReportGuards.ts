/**
 * Guards for the admin report responses. A report component reads its data
 * without checking every field, so anything that is not the expected report
 * (an `{ error }` body, an HTML login or Cloudflare page, an array) must be
 * turned into an error state before it reaches React state: rendered as data,
 * it throws and takes the page down.
 */

export type JsonObject = Record<string, unknown>

export function isJsonObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value)
}

/** The response body as a JSON object, or null for anything else. Never throws. */
export async function readJsonObject(res: Pick<Response, "json">): Promise<JsonObject | null> {
  const body: unknown = await res.json().catch(() => null)
  return isJsonObject(body) ? body : null
}

export type ReportResult = { ok: true; data: JsonObject } | { ok: false; error: string }

/**
 * A report response is usable only when the status is 2xx and the body is a
 * JSON object without an `error` field. Otherwise the server's own message is
 * used when it sent one, else `fallback`.
 */
export function toReportResult(status: { ok: boolean }, body: JsonObject | null, fallback: string): ReportResult {
  if (status.ok && body && !("error" in body)) return { ok: true, data: body }
  return { ok: false, error: typeof body?.error === "string" && body.error ? body.error : fallback }
}

/** The parts of /api/admin/analytics/usage the Feature Usage tab reads without a guard. */
export function isUsageReport(body: JsonObject | null): boolean {
  return !!body && isJsonObject(body.totals) && isJsonObject(body.uniqueUsers) && isJsonObject(body.worksheetBySubject)
    && isJsonObject(body.testBuilderBySubject) && Array.isArray(body.daily)
}
