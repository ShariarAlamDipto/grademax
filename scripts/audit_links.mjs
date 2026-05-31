import { readFileSync, readdirSync, statSync } from "fs"
import { join, relative, sep } from "path"

const APP_ROOT = ".next/server/app"
const PAST_ROOT = ".next/server/app/past-papers"

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    const st = statSync(full)
    if (st.isDirectory()) walk(full, out)
    else if (entry.endsWith(".html")) out.push(full)
  }
  return out
}

const pastFiles = walk(PAST_ROOT)
const allFiles = walk(APP_ROOT)

const builtPaths = new Set()
for (const f of pastFiles) {
  const rel = relative(APP_ROOT, f).split(sep).join("/").replace(/\.html$/, "")
  builtPaths.add("/" + rel)
}

const linkRe = /href="(\/past-papers\/[^"#?]+)"/g
const allLinks = new Map() // url -> { inbound: count, sources: Set }

for (const f of allFiles) {
  const html = readFileSync(f, "utf8")
  const sourceRel = relative(APP_ROOT, f).split(sep).join("/").replace(/\.html$/, "")
  for (const m of html.matchAll(linkRe)) {
    const url = m[1]
    const entry = allLinks.get(url) || { inbound: 0, sources: new Set() }
    entry.inbound += 1
    entry.sources.add(sourceRel)
    allLinks.set(url, entry)
  }
}

const missing = []
const built = []
for (const [url, info] of allLinks) {
  if (builtPaths.has(url)) built.push({ url, ...info })
  else missing.push({ url, ...info })
}

function depth(url) {
  return url.split("/").filter(Boolean).length - 1
}
const buckets = { 1: [], 2: [], 3: [], 4: [] }
for (const m of missing) {
  const d = depth(m.url)
  if (buckets[d]) buckets[d].push(m)
}

// Cluster broken links by source page area to understand who is emitting them
function sourceCategory(s) {
  if (s.startsWith("past-papers/")) {
    const parts = s.split("/").filter(Boolean)
    if (parts.length === 2) return "past-papers/[subject]"
    if (parts.length === 3) return "past-papers/[subject]/[year]"
    if (parts.length === 4) return "past-papers/[subject]/[year]/[season]"
    if (parts.length === 5) return "past-papers/[subject]/[year]/[season]/[paper]"
    return "past-papers/" + parts[0]
  }
  if (s.startsWith("qp/")) return "qp/[slug]"
  if (s.startsWith("subjects/")) return "subjects/"
  return s
}
const sourceCounter = new Map()
for (const m of missing) {
  for (const s of m.sources) {
    const cat = sourceCategory(s)
    sourceCounter.set(cat, (sourceCounter.get(cat) || 0) + 1)
  }
}

console.log("=== Internal past-paper link audit ===")
console.log(`Total built past-paper HTML files: ${builtPaths.size}`)
console.log(`Total HTML files scanned (entire app): ${allFiles.length}`)
console.log(`Unique past-paper hrefs found: ${allLinks.size}`)
console.log(`  -> links to a real built path: ${built.length}`)
console.log(`  -> links to NOTHING (will 404): ${missing.length}`)
console.log()
console.log("Broken-link breakdown by target depth:")
console.log(`  depth 1  /[subject]:                       ${buckets[1].length}`)
console.log(`  depth 2  /[subject]/[year]:                ${buckets[2].length}`)
console.log(`  depth 3  /[subject]/[year]/[season]:       ${buckets[3].length}`)
console.log(`  depth 4  /[subject]/[year]/[season]/paper: ${buckets[4].length}`)
console.log()
console.log("Broken links by emitting source (sum across distinct missing targets):")
const sortedSources = [...sourceCounter.entries()].sort((a, b) => b[1] - a[1])
for (const [cat, n] of sortedSources) console.log(`  ${cat.padEnd(50)} -> ${n}`)
console.log()

function sample(arr, n, label) {
  if (arr.length === 0) return
  console.log(`Sample broken ${label} targets (top ${n} by inbound count):`)
  arr.sort((a, b) => b.inbound - a.inbound)
  for (const x of arr.slice(0, n)) {
    console.log(`  ${x.url}  (linked from ${x.inbound} pages)`)
  }
  console.log()
}
sample(buckets[2], 5, "year")
sample(buckets[3], 8, "session")
sample(buckets[4], 10, "leaf")
