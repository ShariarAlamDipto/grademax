/**
 * Clear all objects from the Cloudflare R2 bucket.
 * Run BEFORE uploading fresh papers from paperlords_download.
 *
 * Usage:
 *   npx tsx scripts/clear-r2-bucket.ts
 */

import { S3Client, ListObjectsV2Command, DeleteObjectsCommand } from '@aws-sdk/client-s3'
import * as fs from 'fs'
import * as path from 'path'
import { config } from 'dotenv'

const envPaths = [
  path.resolve(process.cwd(), '.env.local'),
  path.resolve('C:\\Users\\shari\\grademax', '.env.local'),
]
for (const p of envPaths) {
  if (fs.existsSync(p)) {
    config({ path: p })
    console.log(`Loaded env from: ${p}`)
    break
  }
}

const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID!
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID!
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY!
const R2_BUCKET = process.env.R2_BUCKET_NAME || 'grademax-papers'

const r2 = new S3Client({
  region: 'auto',
  endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: R2_ACCESS_KEY_ID,
    secretAccessKey: R2_SECRET_ACCESS_KEY,
  },
})

async function clearBucket() {
  console.log(`\nClearing all objects from R2 bucket: ${R2_BUCKET}`)
  console.log('═'.repeat(60))

  let totalDeleted = 0
  let continuationToken: string | undefined

  do {
    const listResp = await r2.send(new ListObjectsV2Command({
      Bucket: R2_BUCKET,
      ContinuationToken: continuationToken,
    }))

    const objects = listResp.Contents || []
    if (objects.length === 0) break

    const deleteResp = await r2.send(new DeleteObjectsCommand({
      Bucket: R2_BUCKET,
      Delete: {
        Objects: objects.map(o => ({ Key: o.Key! })),
        Quiet: true,
      },
    }))

    const errCount = deleteResp.Errors?.length || 0
    const deleted = objects.length - errCount
    totalDeleted += deleted

    if (errCount > 0) {
      console.warn(`  ⚠ ${errCount} delete errors in this batch`)
      deleteResp.Errors?.forEach(e => console.warn(`    ${e.Key}: ${e.Message}`))
    }

    console.log(`  Deleted ${deleted} objects (running total: ${totalDeleted})`)
    continuationToken = listResp.IsTruncated ? listResp.NextContinuationToken : undefined
  } while (continuationToken)

  console.log('═'.repeat(60))
  console.log(`✅ Done. Total objects deleted: ${totalDeleted}`)
  console.log('\nNext step: npx tsx scripts/upload-papers-r2.ts')
}

clearBucket().catch(console.error)
