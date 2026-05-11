#!/usr/bin/env node

const fs = require("fs")
const path = require("path")

for (const file of ["docker.env", ".env.local", ".env"]) {
  const envPath = path.resolve(process.cwd(), file)
  if (!fs.existsSync(envPath)) continue
  const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/)
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith("#")) continue
    const equalsIndex = trimmed.indexOf("=")
    if (equalsIndex === -1) continue
    const key = trimmed.slice(0, equalsIndex).trim()
    const value = trimmed.slice(equalsIndex + 1).trim().replace(/^['"]|['"]$/g, "")
    if (key && process.env[key] === undefined) process.env[key] = value
  }
}

const persistRoot = path.resolve(process.env.GRADEMAX_PERSIST_DIR || "../grademax-persistent")
const mode = process.argv.includes("--move") ? "move" : "copy"
const link = process.argv.includes("--link")
const runtimeDirs = ["data", "logs", "output", "config"]

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true })
}

function copyRecursive(source, target) {
  if (!fs.existsSync(source)) return
  const stat = fs.lstatSync(source)
  if (stat.isSymbolicLink()) return
  if (stat.isDirectory()) {
    ensureDir(target)
    for (const entry of fs.readdirSync(source)) {
      copyRecursive(path.join(source, entry), path.join(target, entry))
    }
    return
  }
  ensureDir(path.dirname(target))
  if (!fs.existsSync(target)) fs.copyFileSync(source, target)
}

for (const dir of runtimeDirs) {
  const source = path.resolve(process.cwd(), dir)
  const target = path.join(persistRoot, dir)
  ensureDir(target)
  copyRecursive(source, target)

  if (mode === "move" && fs.existsSync(source) && !fs.lstatSync(source).isSymbolicLink()) {
    fs.rmSync(source, { recursive: true, force: true })
    if (link) {
      const relativeTarget = path.relative(path.dirname(source), target)
      fs.symlinkSync(relativeTarget, source, "dir")
    } else {
      ensureDir(source)
    }
  }

  console.log(`${mode} ${dir} -> ${target}`)
}

const postgresDir = path.resolve(process.env.POSTGRES_DATA_DIR || "../postgres_data")
ensureDir(postgresDir)
console.log(`ensure postgres -> ${postgresDir}`)
