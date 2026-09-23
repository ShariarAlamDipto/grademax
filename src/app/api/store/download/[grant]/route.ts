import { NextRequest, NextResponse } from "next/server"
import { getSupabaseAdmin } from "@/lib/supabaseAdmin"
import { verifyDownloadGrant } from "@/lib/store/downloadGrant"
import { presignStoreDownload, isStoreBucketConfigured } from "@/lib/store/r2Store"
import { checkRateLimitByIp, getClientIp } from "@/lib/store/rateLimit"

/**
 * GET /api/store/download/[grant] — redeem a download grant.
 *
 * Three gates, in order: the signature must verify and be unexpired; the
 * entitlement must still be live (payment verified, not revoked, allowance
 * unspent); and only then is a presigned R2 URL minted.
 *
 * The file is NOT streamed through this route. These PDFs run to 90MB, which
 * would exceed the serverless response limit, time out, and bill the egress
 * twice. The buyer is redirected to a five-minute R2 link instead.
 */
export const dynamic = "force-dynamic"

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ grant: string }> }
) {
  const { grant } = await params

  if (!(await checkRateLimitByIp("download"))) {
    return NextResponse.json({ error: "Too many download attempts. Please wait a few minutes." }, { status: 429 })
  }

  const checked = verifyDownloadGrant(grant)
  if (!checked.ok) {
    const message = checked.reason === "expired"
      ? "This download link has expired. Open your order again to get a fresh one."
      : "This download link is not valid."
    return NextResponse.json({ error: message }, { status: 403 })
  }

  if (!isStoreBucketConfigured()) {
    return NextResponse.json(
      { error: "Downloads are not available yet. Please contact us and we will send your files." },
      { status: 503 }
    )
  }

  const db = getSupabaseAdmin()
  if (!db) return NextResponse.json({ error: "Temporarily unavailable." }, { status: 503 })

  // Spends one download and re-checks payment, revocation and the allowance in
  // a single guarded statement, so parallel requests cannot both slip through.
  const ip = await getClientIp()
  const { data, error } = await db.rpc("store_consume_download", {
    p_entitlement: checked.entitlementId,
    p_ip: ip,
  })

  const result = data as { ok?: boolean; variant_id?: string; product_title?: string } | null
  if (error || !result?.ok) {
    return NextResponse.json(
      { error: "This download is no longer available. If you believe this is a mistake, contact us with your order number." },
      { status: 403 }
    )
  }

  // Resolve the files for this variant. Multiple rows is the normal case: a
  // workbook and its mark-scheme volume are separate PDFs.
  const { data: files } = await db
    .from("store_variant_files")
    .select("label, r2_key, file_name, file_bytes")
    .eq("variant_id", result.variant_id!)
    .order("sort_order", { ascending: true })

  if (!files?.length) {
    return NextResponse.json(
      { error: "Your files are being prepared. Please contact us with your order number." },
      { status: 503 }
    )
  }

  const rows = files as { label: string; r2_key: string; file_name: string; file_bytes: number | null }[]

  const links = await Promise.all(
    rows.map(async f => ({
      label: f.label,
      fileName: f.file_name,
      bytes: f.file_bytes,
      url: await presignStoreDownload(f.r2_key, f.file_name),
    }))
  )

  // A single-file product redirects straight to the file; a multi-file one
  // returns the list, because a browser can only follow one redirect.
  const wantsJson = req.nextUrl.searchParams.get("format") === "json"
  if (links.length === 1 && !wantsJson) {
    return NextResponse.redirect(links[0]!.url, { status: 302 })
  }

  return NextResponse.json({
    productTitle: result.product_title,
    files: links,
    note: "These links are valid for a few minutes. Reopen your order for fresh ones.",
  })
}
