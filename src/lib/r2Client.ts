import { S3Client } from "@aws-sdk/client-s3"

const ACCOUNT_ID = process.env.R2_ACCOUNT_ID!
export const R2_BUCKET = process.env.R2_BUCKET_NAME || "grademax-papers"
export const R2_PUBLIC_URL = process.env.NEXT_PUBLIC_R2_PUBLIC_URL || `https://pub-b96af5a8f7044337bcb17a51b3fd4a60.r2.dev`

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
