/**
 * fix-fpm-and-datafiles.ts
 *
 * 1. Consolidates the duplicate "Further Pure Mathematics" subject rows:
 *    - Source:      [International GCSE] (code 9FM0) — has 86 papers
 *    - Destination: [IGCSE]              (code 4PM1) — empty
 *    Re-points all papers to the IGCSE row, then deletes the orphaned subject.
 *
 * 2. Reports paper status to confirm the outcome.
 *
 * NB: ALTER TABLE for `data_file_url` is in supabase/migrations/10_*.sql —
 *     apply that via the Supabase SQL editor before uploading data files.
 *
 * Usage:
 *   npx tsx --env-file=.env.local scripts/fix-fpm-and-datafiles.ts
 *   npx tsx --env-file=.env.local scripts/fix-fpm-and-datafiles.ts --dry-run
 */

import { createClient } from '@supabase/supabase-js'
import * as fs from 'fs'
import * as path from 'path'
import { config } from 'dotenv'

const envPaths = [
  path.resolve(process.cwd(), '.env.local'),
  path.resolve('C:\\Users\\shari\\grademax', '.env.local'),
]
for (const p of envPaths) {
  if (fs.existsSync(p)) { config({ path: p }); break }
}

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const DRY_RUN = process.argv.includes('--dry-run')

async function main() {
  console.log(DRY_RUN ? '⚠ DRY RUN' : 'Live run')

  const { data: rows, error } = await supabase
    .from('subjects')
    .select('id, name, level, code')
    .eq('name', 'Further Pure Mathematics')
  if (error) throw error
  if (!rows || rows.length === 0) { console.log('No FPM subjects found'); return }

  const igcse = rows.find(r => r.code === '4PM1')
  const legacy = rows.find(r => r.code === '9FM0')
  if (!igcse) {
    console.error('Missing IGCSE 4PM1 row — aborting')
    process.exit(1)
  }
  if (!legacy) {
    console.log('No legacy 9FM0 row to consolidate — nothing to do')
    return
  }

  console.log(`IGCSE 4PM1  : ${igcse.id}`)
  console.log(`Legacy 9FM0 : ${legacy.id}`)

  const { count: legacyCount } = await supabase
    .from('papers')
    .select('id', { count: 'exact', head: true })
    .eq('subject_id', legacy.id)
  console.log(`Papers on legacy row: ${legacyCount ?? 0}`)

  if (!DRY_RUN && (legacyCount ?? 0) > 0) {
    const { error: updErr } = await supabase
      .from('papers')
      .update({ subject_id: igcse.id })
      .eq('subject_id', legacy.id)
    if (updErr) {
      console.error('Failed to re-point papers:', updErr)
      process.exit(1)
    }
    console.log(`✓ Re-pointed ${legacyCount} papers to IGCSE row`)
  }

  if (!DRY_RUN) {
    // Re-point any other tables that reference this subject (tests, worksheets,
    // topics, etc.) so the FK delete succeeds.
    const dependentTables = ['tests', 'worksheets', 'topics']
    for (const table of dependentTables) {
      const { error: depErr, count: depCount } = await supabase
        .from(table)
        .update({ subject_id: igcse.id }, { count: 'exact' })
        .eq('subject_id', legacy.id)
      if (depErr && depErr.code !== '42P01') {
        console.warn(`  Could not update ${table}:`, depErr.message)
      } else if ((depCount ?? 0) > 0) {
        console.log(`  ✓ Re-pointed ${depCount} rows in ${table}`)
      }
    }

    const { error: delErr } = await supabase
      .from('subjects')
      .delete()
      .eq('id', legacy.id)
    if (delErr) {
      console.error('Failed to delete legacy subject:', delErr)
      process.exit(1)
    }
    console.log('✓ Deleted legacy 9FM0 subject row')
  }

  const { count: finalCount } = await supabase
    .from('papers')
    .select('id', { count: 'exact', head: true })
    .eq('subject_id', igcse.id)
  console.log(`Papers on IGCSE row now: ${finalCount ?? 0}`)
}

main().catch(err => { console.error(err); process.exit(1) })
