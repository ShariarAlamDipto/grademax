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
