/**
 * upload-ict-papers.ts
 *
 * Uploads IGCSE ICT past papers from data/IGCSE FINAL/ICT/ to Cloudflare R2
 * and upserts subjects + papers into Supabase.
 *
 * Uses the SAME R2 path convention as the admin panel upload route:
 *   ICT/{Year}/{Session}/{filename}.pdf
 *   e.g. ICT/2024/May-Jun/ICT_2024_May-Jun_Paper_1_QP.pdf
 *
 * This ensures the admin panel audit (which looks under "ICT/" prefix) finds the files.
 *
 * Usage:
 *   npx tsx --env-file=.env.local scripts/upload-ict-papers.ts
 *   npx tsx --env-file=.env.local scripts/upload-ict-papers.ts --dry-run
 */

import { S3Client, PutObjectCommand, HeadObjectCommand } from "@aws-sdk/client-s3"
import { createClient } from "@supabase/supabase-js"
import * as fs from "fs"
import * as path from "path"
import { config } from "dotenv"

// ─── Load env ─────────────────────────────────────────────────────────────────

const envPaths = [
  path.resolve(process.cwd(), ".env.local"),
  path.resolve("C:\\Users\\shari\\grademax", ".env.local"),
]
for (const p of envPaths) {
  if (fs.existsSync(p)) {
    config({ path: p })
    console.log(`Loaded env from: ${p}`)
    break
  }
}

// ─── Config ───────────────────────────────────────────────────────────────────

const ICT_DIR       = "C:\\Users\\shari\\grademax\\data\\IGCSE FINAL\\ICT"
const SUBJECT_NAME  = "ICT"
const SUBJECT_CODE  = "4IT1"
const SUBJECT_LEVEL = "igcse"
const SUBJECT_BOARD = "Edexcel"
const R2_FOLDER     = "ICT"          // Admin panel convention: name, no spaces

const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID!
const R2_ACCESS_KEY = process.env.R2_ACCESS_KEY_ID!
const R2_SECRET_KEY = process.env.R2_SECRET_ACCESS_KEY!
const R2_BUCKET     = process.env.R2_BUCKET_NAME || "grademax-papers"
const R2_PUBLIC_URL = process.env.NEXT_PUBLIC_R2_PUBLIC_URL!
const SUPABASE_URL  = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_KEY  = process.env.SUPABASE_SERVICE_ROLE_KEY!

const DRY_RUN = process.argv.includes("--dry-run")

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeR2Client(): S3Client {
  return new S3Client({
    region: "auto",
    endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId: R2_ACCESS_KEY, secretAccessKey: R2_SECRET_KEY },
  })
}

async function fileExistsInR2(r2: S3Client, key: string): Promise<boolean> {
  try {
    await r2.send(new HeadObjectCommand({ Bucket: R2_BUCKET, Key: key }))
    return true
  } catch {
    return false
  }
}

async function uploadToR2(r2: S3Client, localPath: string, r2Key: string): Promise<string> {
  const exists = await fileExistsInR2(r2, r2Key)
  if (exists) {
    process.stdout.write("(skipped — already in R2) ")
    return `${R2_PUBLIC_URL}/${r2Key}`
  }
  if (DRY_RUN) {
    process.stdout.write("(dry-run skip) ")
    return `${R2_PUBLIC_URL}/${r2Key}`
  }
  const body = fs.readFileSync(localPath)
  await r2.send(new PutObjectCommand({
    Bucket: R2_BUCKET,
    Key: r2Key,
    Body: body,
    ContentType: "application/pdf",
    CacheControl: "public, max-age=31536000, immutable",
  }))
  return `${R2_PUBLIC_URL}/${r2Key}`
}

/**
 * Parse filename: ICT_2024_May-Jun_Paper_1_QP.pdf → { paperNumber: "1", type: "QP" }
 * Works for: 1, 2, 1R, 2R, 3H, etc.
 */
function parseFilename(filename: string): { paperNumber: string; type: "QP" | "MS" } | null {
  const base = filename.replace(/\.pdf$/i, "")
  const paperIdx = base.lastIndexOf("_Paper_")
  if (paperIdx === -1) return null
  const afterPaper = base.substring(paperIdx + "_Paper_".length)
  const lastUnderscore = afterPaper.lastIndexOf("_")
  if (lastUnderscore === -1) return null
  const paperNumber = afterPaper.substring(0, lastUnderscore).toUpperCase()
  const typeStr = afterPaper.substring(lastUnderscore + 1).toUpperCase()
  if (typeStr !== "QP" && typeStr !== "MS") return null
  if (!paperNumber) return null
  return { paperNumber, type: typeStr }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log("╔══════════════════════════════════════════════════════════╗")
  console.log("║         GradeMax ICT Papers → R2 + Supabase             ║")
  console.log("╚══════════════════════════════════════════════════════════╝")
  if (DRY_RUN) console.log("  ⚠  DRY RUN — nothing will be uploaded or written to DB\n")

  const missing = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
    "NEXT_PUBLIC_R2_PUBLIC_URL", "NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    .filter(k => !process.env[k])
  if (missing.length) {
    console.error("✗ Missing env vars:", missing.join(", "))
    process.exit(1)
  }
  if (!fs.existsSync(ICT_DIR)) {
    console.error("✗ ICT source directory not found:", ICT_DIR)
    process.exit(1)
  }

  const r2       = makeR2Client()
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

  console.log(`\nR2 Bucket  : ${R2_BUCKET}`)
  console.log(`R2 Base URL: ${R2_PUBLIC_URL}`)
  console.log(`ICT Dir    : ${ICT_DIR}`)
  console.log(`R2 Prefix  : ${R2_FOLDER}/`)

  // ── Ensure subject exists in DB ──────────────────────────────────────────
  let subjectId: string

  const { data: existingSubject } = await supabase
    .from("subjects")
    .select("id")
    .eq("name", SUBJECT_NAME)
    .limit(1)

  if (existingSubject && existingSubject.length > 0) {
    subjectId = existingSubject[0].id
    console.log(`\n✓ Subject "${SUBJECT_NAME}" found in DB — ID: ${subjectId}`)
  } else {
    if (DRY_RUN) {
      console.log(`\n  (dry-run) Would insert subject "${SUBJECT_NAME}"`)
      subjectId = "dry-run-id"
    } else {
      const { data: inserted, error } = await supabase
        .from("subjects")
        .insert({ name: SUBJECT_NAME, code: SUBJECT_CODE, board: SUBJECT_BOARD, level: SUBJECT_LEVEL })
        .select("id")
        .single()
      if (error || !inserted) {
        console.error(`✗ Failed to insert subject:`, error?.message)
        process.exit(1)
      }
      subjectId = inserted.id
      console.log(`\n✓ Inserted subject "${SUBJECT_NAME}" — ID: ${subjectId}`)
    }
  }

  // ── Walk year / session / files ───────────────────────────────────────────
  let uploaded = 0
  let skipped  = 0
  let errors   = 0

  const years = fs.readdirSync(ICT_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}$/.test(d.name))
    .map(d => d.name)
    .sort((a, b) => parseInt(b) - parseInt(a))  // newest first

  for (const year of years) {
    const yearDir = path.join(ICT_DIR, year)
    const sessions = fs.readdirSync(yearDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)
      .sort()

    for (const session of sessions) {
      const sessionDir = path.join(yearDir, session)
      const seasonDb   = session.toLowerCase()  // "jan", "may-jun", "oct-nov"

      const pdfs = fs.readdirSync(sessionDir).filter(f => /\.pdf$/i.test(f)).sort()

      // Group QP + MS by paper number
      const groups = new Map<string, { qpFile?: string; msFile?: string; qpName?: string; msName?: string }>()

      for (const pdf of pdfs) {
        const parsed = parseFilename(pdf)
        if (!parsed) {
          console.warn(`    ⚠ Unrecognised filename: ${pdf}`)
          errors++
          continue
        }
        if (!groups.has(parsed.paperNumber)) groups.set(parsed.paperNumber, {})
        const g = groups.get(parsed.paperNumber)!
        const fullPath = path.join(sessionDir, pdf)
        if (parsed.type === "QP") { g.qpFile = fullPath; g.qpName = pdf }
        else                      { g.msFile = fullPath; g.msName = pdf }
      }

      for (const [paperNumber, g] of [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))) {
        process.stdout.write(`  ${year} ${session.padEnd(8)} Paper ${paperNumber.padEnd(4)}`)

        try {
          let pdfUrl: string | null = null
          let msUrl:  string | null = null

          // R2 paths use the original session case (e.g. "May-Jun"), same as admin panel
          if (g.qpFile && g.qpName) {
            const key = `${R2_FOLDER}/${year}/${session}/${g.qpName}`
            pdfUrl = await uploadToR2(r2, g.qpFile, key)
            process.stdout.write(`QP:✓ `)
          } else {
            process.stdout.write(`QP:— `)
          }

          if (g.msFile && g.msName) {
            const key = `${R2_FOLDER}/${year}/${session}/${g.msName}`
            msUrl = await uploadToR2(r2, g.msFile, key)
            process.stdout.write(`MS:✓`)
          } else {
            process.stdout.write(`MS:—`)
          }

          if (!DRY_RUN) {
            // Upsert DB row
            const { data: existPaper } = await supabase
              .from("papers")
              .select("id, pdf_url, markscheme_pdf_url")
              .eq("subject_id", subjectId)
              .eq("year", parseInt(year))
              .eq("season", seasonDb)
              .eq("paper_number", paperNumber)
              .maybeSingle()

            if (existPaper) {
              const updates: Record<string, string | null> = {}
              if (pdfUrl && !existPaper.pdf_url) updates.pdf_url = pdfUrl
              if (msUrl  && !existPaper.markscheme_pdf_url) updates.markscheme_pdf_url = msUrl
              // Always update URL if we just uploaded (might have changed)
              if (pdfUrl) updates.pdf_url = pdfUrl
              if (msUrl)  updates.markscheme_pdf_url = msUrl
              if (Object.keys(updates).length > 0) {
                await supabase.from("papers").update(updates).eq("id", existPaper.id)
              }
              skipped++
            } else {
              const { error: ie } = await supabase.from("papers").insert({
                subject_id: subjectId,
                paper_number: paperNumber,
                year: parseInt(year),
                season: seasonDb,
                pdf_url: pdfUrl,
                markscheme_pdf_url: msUrl,
              })
              if (ie) {
                process.stdout.write(` ✗ DB insert: ${ie.message}`)
                errors++
              } else {
                uploaded++
              }
            }
          }

          process.stdout.write("\n")
        } catch (err) {
          process.stdout.write(` ✗ ${err}\n`)
          errors++
        }
      }
    }
  }

  console.log("\n══════════════════════════════════════════════════════════")
  if (DRY_RUN) {
    console.log("  Dry run complete — run without --dry-run to upload for real")
  } else {
    console.log("✅  ICT upload complete!")
    console.log(`    New papers inserted : ${uploaded}`)
    console.log(`    Existing updated    : ${skipped}`)
    console.log(`    Errors              : ${errors}`)
  }
  console.log("══════════════════════════════════════════════════════════")
}

main().catch(err => { console.error("Fatal:", err); process.exit(1) })
