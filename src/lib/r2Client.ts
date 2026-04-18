import { S3Client } from "@aws-sdk/client-s3"

if (!process.env.R2_ACCOUNT_ID) {
  throw new Error("Missing required env var: R2_ACCOUNT_ID")
}
if (!process.env.NEXT_PUBLIC_R2_PUBLIC_URL) {
  throw new Error("Missing required env var: NEXT_PUBLIC_R2_PUBLIC_URL")
}

const ACCOUNT_ID = process.env.R2_ACCOUNT_ID
export const R2_BUCKET = process.env.R2_BUCKET_NAME || "grademax-papers"
export const R2_PUBLIC_URL = process.env.NEXT_PUBLIC_R2_PUBLIC_URL

let _r2Client: S3Client | null = null

export function getR2Client(): S3Client {
  if (_r2Client) return _r2Client
  _r2Client = new S3Client({
    region: "auto",
    endpoint: `https://${ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: process.env.R2_ACCESS_KEY_ID!,
      secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    },
  })
  return _r2Client
}
