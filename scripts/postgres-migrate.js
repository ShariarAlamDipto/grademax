#!/usr/bin/env node

const fs = require("fs")
const path = require("path")
const { Client } = require("pg")
const dotenv = require("dotenv")

for (const file of [".env.local", ".env", "docker.env"]) {
  const envPath = path.resolve(process.cwd(), file)
  if (fs.existsSync(envPath)) dotenv.config({ path: envPath, override: false })
}

const databaseUrl = process.env.DATABASE_URL
if (!databaseUrl) {
  console.error("DATABASE_URL is required")
  process.exit(1)
}

// ─────────────────────────────────────────────────────────────────────────────
// PRODUCTION GUARD
//
// These migrations build the NEW self-hosted schema and contain destructive
// statements (DROP TABLE ... CASCADE). Running them against the production
// Supabase database destroyed the live tables on 2026-06-01 AND 2026-06-11
// (both times via a DATABASE_URL in docker.env / .env.local that pointed at
// Supabase). They are only ever meant for the local/VM Docker Postgres.
//
// If you are CERTAIN you want to run them against a Supabase host, set:
//   ALLOW_SUPABASE_MIGRATIONS=I_UNDERSTAND_THIS_CAN_DESTROY_PRODUCTION
// ─────────────────────────────────────────────────────────────────────────────
let targetHost = ""
try {
  targetHost = new URL(databaseUrl).hostname
} catch {
  console.error("DATABASE_URL is not a parseable URL — refusing to run migrations blind")
  process.exit(1)
}

const isSupabaseHost = /supabase/i.test(targetHost)
const override =
  process.env.ALLOW_SUPABASE_MIGRATIONS === "I_UNDERSTAND_THIS_CAN_DESTROY_PRODUCTION"

console.log(`migration target host: ${targetHost}`)

if (isSupabaseHost && !override) {
  console.error("")
  console.error("REFUSING TO RUN: DATABASE_URL points at a Supabase host.")
  console.error(`  host: ${targetHost}`)
  console.error("")
  console.error("These db/migrations are for the self-hosted Docker Postgres only.")
  console.error("Applying them to production Supabase dropped the live tables twice")
  console.error("(2026-06-01, 2026-06-11). If you really intend this, set")
  console.error("  ALLOW_SUPABASE_MIGRATIONS=I_UNDERSTAND_THIS_CAN_DESTROY_PRODUCTION")
  console.error("and take a backup first: python scripts/dump_supabase_schema.py")
  process.exit(1)
}

const migrationsDir = path.resolve(process.cwd(), "db", "migrations")
const migrations = fs
  .readdirSync(migrationsDir)
  .filter((file) => file.endsWith(".sql"))
  .sort()

async function main() {
  const client = new Client({ connectionString: databaseUrl })
  await client.connect()

  await client.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename TEXT PRIMARY KEY,
      applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `)

  for (const filename of migrations) {
    const applied = await client.query(
      "SELECT 1 FROM schema_migrations WHERE filename = $1",
      [filename]
    )
    if (applied.rowCount) {
      console.log(`skip ${filename}`)
      continue
    }

    const sql = fs.readFileSync(path.join(migrationsDir, filename), "utf8")
    console.log(`apply ${filename}`)
    await client.query(sql)
    await client.query("INSERT INTO schema_migrations (filename) VALUES ($1)", [filename])
  }

  await client.end()
  console.log("postgres migrations complete")
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
