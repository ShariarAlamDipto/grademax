/**
 * Apply one SQL migration file to the database in DATABASE_URL.
 *
 *   node --env-file=.env.local scripts/apply-migration.mjs supabase/migrations/21_store_schema.sql
 *
 * The file is sent as a single statement batch so its own BEGIN/COMMIT controls
 * the transaction — a migration that fails half way must not leave the schema
 * in a partial state.
 */
import { readFileSync } from "node:fs"
import pg from "pg"

const file = process.argv[2]
if (!file) {
  console.error("usage: apply-migration.mjs <path-to-sql>")
  process.exit(1)
}

const connectionString = process.env.DATABASE_URL
if (!connectionString) {
  console.error("DATABASE_URL is not set")
  process.exit(1)
}

const sql = readFileSync(file, "utf8")
const client = new pg.Client({
  connectionString,
  ssl: { rejectUnauthorized: false },
})

try {
  await client.connect()
  await client.query(sql)
  console.log(`OK  ${file}`)
} catch (err) {
  console.error(`FAIL ${file}`)
  console.error(`${err.severity ?? "ERROR"}: ${err.message}`)
  if (err.position) {
    const upto = sql.slice(0, Number(err.position))
    const line = upto.split("\n").length
    console.error(`  at line ${line}: ${sql.split("\n")[line - 1]?.trim()}`)
  }
  process.exitCode = 1
} finally {
  await client.end()
}
