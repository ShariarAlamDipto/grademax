/**
 * Access to the PRIVATE bucket that holds the paid PDFs.
 *
 * WHY THIS IS NOT `src/lib/r2Client.ts`
 * -------------------------------------
 * The papers bucket (`grademax-papers`) is served through a `pub-*.r2.dev`
 * domain, which makes the WHOLE bucket world-readable — verified by fetching a
 * key anonymously and getting HTTP 200. Putting a paid workbook in that bucket
 * would publish it. Paid files therefore live in a separate bucket with no
 * public binding, reachable only through a short-lived presigned URL.
 *
 * Previews are the opposite case: they are meant to be public, are only a
 * dozen pages, and are served straight off the existing public bucket.
 */
import { S3Client, GetObjectCommand, HeadObjectCommand } from "@aws-sdk/client-s3"
import { getSignedUrl } from "@aws-sdk/s3-request-presigner"

/** Seconds a download link stays valid. Long enough to start a 90MB download. */
export const PRESIGN_TTL_SECONDS = 300

export const STORE_BUCKET = process.env.R2_STORE_BUCKET || ""

let client: S3Client | null = null

/**
 * Throws rather than falling back to the public bucket. A misconfigured
 * environment must fail loudly at the point of use, because the "helpful"
 * fallback here would be to serve paid files from a public URL.
 */
export function getStoreR2Client(): S3Client {
  if (client) return client

  const accountId = process.env.R2_ACCOUNT_ID
  const accessKeyId = process.env.R2_STORE_ACCESS_KEY_ID || process.env.R2_ACCESS_KEY_ID
  const secretAccessKey = process.env.R2_STORE_SECRET_ACCESS_KEY || process.env.R2_SECRET_ACCESS_KEY

  if (!STORE_BUCKET) {
    throw new Error(
      "R2_STORE_BUCKET is not set. Paid files must live in a PRIVATE bucket — " +
      "the papers bucket is public and would expose them."
    )
  }
  if (!accountId || !accessKeyId || !secretAccessKey) {
    throw new Error("Missing R2 credentials for the store bucket")
  }

  client = new S3Client({
    region: "auto",
    endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId, secretAccessKey },
  })
  return client
}

export function isStoreBucketConfigured(): boolean {
  return Boolean(STORE_BUCKET && process.env.R2_ACCOUNT_ID)
}

/**
 * A time-limited direct link to R2.
 *
 * The file is NOT proxied through the server: these PDFs run to 90MB, which
 * would blow past the serverless response limit and bill egress twice.
 * `ResponseContentDisposition` makes the browser save it under a sensible name
 * rather than the opaque object key.
 */
export async function presignStoreDownload(
  r2Key: string,
  downloadFileName: string
): Promise<string> {
  const safeName = downloadFileName.replace(/["\\]/g, "").slice(0, 180)
  const command = new GetObjectCommand({
    Bucket: STORE_BUCKET,
    Key: r2Key,
    ResponseContentDisposition: `attachment; filename="${safeName}"`,
    ResponseContentType: "application/pdf",
  })
  return getSignedUrl(getStoreR2Client(), command, { expiresIn: PRESIGN_TTL_SECONDS })
}

/** Confirm an object exists before a product is switched on. */
export async function storeObjectExists(r2Key: string): Promise<boolean> {
  try {
    await getStoreR2Client().send(
      new HeadObjectCommand({ Bucket: STORE_BUCKET, Key: r2Key })
    )
    return true
  } catch {
    return false
  }
}

/** Public URL for a preview PDF, which lives in the public papers bucket. */
export function publicPreviewUrl(previewKey: string | null | undefined): string | null {
  if (!previewKey) return null
  const base = process.env.NEXT_PUBLIC_R2_PUBLIC_URL
  if (!base) return null
  return `${base}/${previewKey.split("/").map(encodeURIComponent).join("/")}`
}
