/**
 * Allow the GradeMax site to PUT lecture files straight to R2 from the browser.
 *
 * Teacher lecture uploads larger than ~4.5 MB cannot go through the Vercel
 * serverless route (the platform rejects the request body at the edge), so the
 * browser uploads them to R2 with a presigned URL instead. That is a
 * cross-origin PUT, which R2 refuses unless the bucket carries a CORS policy
 * naming our origins.
 *
 * Run once per bucket:
 *   node scripts/set-r2-cors.js
 *   node scripts/set-r2-cors.js --show     # print the current policy only
 *
 * Requires R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY. The API token
 * needs bucket-level (not just object-level) permissions to change CORS.
 */
const {
  S3Client,
  PutBucketCorsCommand,
  GetBucketCorsCommand,
} = require("@aws-sdk/client-s3")

const ACCOUNT_ID = process.env.R2_ACCOUNT_ID
const ACCESS_KEY = process.env.R2_ACCESS_KEY_ID
const SECRET_KEY = process.env.R2_SECRET_ACCESS_KEY
const BUCKET = process.env.R2_BUCKET_NAME || "grademax-papers"

const ALLOWED_ORIGINS = [
  "https://grademax.me",
  "https://www.grademax.me",
  "http://localhost:3000",
]

if (!ACCOUNT_ID || !ACCESS_KEY || !SECRET_KEY) {
  console.error(
    "Missing R2 credentials. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY."
  )
  process.exit(1)
}

const r2 = new S3Client({
  region: "auto",
  endpoint: `https://${ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId: ACCESS_KEY, secretAccessKey: SECRET_KEY },
})

async function show() {
  try {
    const current = await r2.send(new GetBucketCorsCommand({ Bucket: BUCKET }))
    console.log(JSON.stringify(current.CORSRules, null, 2))
  } catch (e) {
    if (e.name === "NoSuchCORSConfiguration") {
      console.log(`Bucket "${BUCKET}" has no CORS policy set.`)
    } else {
      console.error(`Could not read CORS: ${e.name} - ${e.message}`)
      process.exitCode = 1
    }
  }
}

async function apply() {
  // Preview deployments get their own vercel.app hostname per build, so they
  // are intentionally not listed — test large uploads on localhost or prod.
  const rules = [
    {
      AllowedOrigins: ALLOWED_ORIGINS,
      AllowedMethods: ["PUT", "GET", "HEAD"],
      AllowedHeaders: ["content-type"],
      ExposeHeaders: ["ETag"],
      MaxAgeSeconds: 3600,
    },
  ]

  try {
    await r2.send(
      new PutBucketCorsCommand({
        Bucket: BUCKET,
        CORSConfiguration: { CORSRules: rules },
      })
    )
    console.log(`✓ CORS applied to "${BUCKET}" for:`)
    ALLOWED_ORIGINS.forEach((o) => console.log(`    ${o}`))
  } catch (e) {
    console.error(`✗ Failed to set CORS (${e.$metadata?.httpStatusCode}): ${e.name} - ${e.message}`)
    if (e.$metadata?.httpStatusCode === 403) {
      console.error(
        "\n  → The R2 API token needs bucket-level permissions to edit CORS.\n" +
          "  → Alternatively set it in the Cloudflare dashboard:\n" +
          "    R2 → " + BUCKET + " → Settings → CORS Policy"
      )
    }
    process.exitCode = 1
  }
}

const main = process.argv.includes("--show") ? show : apply
main()
