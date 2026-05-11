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

function extractSubjects() {
  const source = fs.readFileSync(path.resolve("src/lib/subjects.ts"), "utf8")
  const block = source.match(/export const subjects: Subject\[\] = \[([\s\S]*?)\]\n/)?.[1]
  if (!block) throw new Error("Could not find subjects array")

  const objectMatches = block.match(/\{[^{}]*slug:[^{}]*\}/g) || []
  return objectMatches
    .map((entry) => {
      const get = (key) => entry.match(new RegExp(`${key}:\\s*"([^"]+)"`))?.[1] || null
      return {
        slug: get("slug"),
        name: get("name"),
        level: get("level"),
        colorKey: get("colorKey"),
        dataFolder: get("dataFolder"),
      }
    })
    .filter((subject) => subject.slug && subject.name && subject.level)
}

function inferCode(subject) {
  const known = {
    physics: "4PH1",
    chemistry: "4CH1",
    biology: "4BI1",
    "human-biology": "4HB1",
    "maths-a": "4MA1",
    "maths-b": "4MB1",
    "further-pure-maths": "4PM1",
    ict: "4IT1",
    "computer-science": "4CP0",
    "pure-mathematics-1": "WMA11",
    "pure-mathematics-2": "WMA12",
    "pure-mathematics-3": "WMA13",
    "pure-mathematics-4": "WMA14",
    "mechanics-1": "WME01",
    "mechanics-2": "WME02",
    "mechanics-3": "WME03",
    "statistics-1": "WST01",
    "statistics-2": "WST02",
    "statistics-3": "WST03",
    "decision-mathematics-1": "WDM11",
    "further-pure-maths-1": "WFM01",
    "further-pure-maths-2": "WFM02",
    "further-pure-maths-3": "WFM03",
    "ial-biology": "WBI",
    "ial-chemistry": "WCH",
    "ial-physics": "WPH",
  }
  return known[subject.slug] || subject.slug.toUpperCase().replace(/[^A-Z0-9]+/g, "_")
}

async function main() {
  const subjects = extractSubjects()
  const client = new Client({ connectionString: databaseUrl })
  await client.connect()

  for (const subject of subjects) {
    await client.query(
      `
        INSERT INTO subjects (slug, code, name, board, level, color_key, data_folder)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (slug) DO UPDATE SET
          code = EXCLUDED.code,
          name = EXCLUDED.name,
          board = EXCLUDED.board,
          level = EXCLUDED.level,
          color_key = EXCLUDED.color_key,
          data_folder = EXCLUDED.data_folder
      `,
      [
        subject.slug,
        inferCode(subject),
        subject.name,
        "Edexcel",
        subject.level.toUpperCase(),
        subject.colorKey,
        subject.dataFolder,
      ]
    )
  }

  const physicsTopics = [
    ["1", "Forces and motion", "Newton's laws, acceleration, velocity, momentum"],
    ["2", "Electricity", "Current, voltage, resistance, circuits, power"],
    ["3", "Waves", "Sound, light, reflection, refraction, electromagnetic spectrum"],
    ["4", "Energy resources", "Renewable and non-renewable energy, efficiency, conservation"],
    ["5", "Solids, liquids and gases", "States of matter, pressure, density, kinetic theory"],
    ["6", "Magnetism and electromagnetism", "Magnetic fields, motors, generators, transformers"],
    ["7", "Radioactivity and particles", "Atoms, isotopes, radiation, half-life, nuclear physics"],
    ["8", "Astrophysics", "Universe, stars, planets, solar system, cosmology"],
  ]

  const physics = await client.query("SELECT id FROM subjects WHERE slug = 'physics' LIMIT 1")
  if (physics.rowCount) {
    for (const [code, name, description] of physicsTopics) {
      await client.query(
        `
          INSERT INTO topics (subject_id, code, name, description)
          VALUES ($1, $2, $3, $4)
          ON CONFLICT (subject_id, code) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description
        `,
        [physics.rows[0].id, code, name, description]
      )
    }
  }

  await client.end()
  console.log(`seeded ${subjects.length} subjects`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
