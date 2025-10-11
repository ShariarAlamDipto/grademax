/**
 * clean_papers.ts
 * Delete all papers and related data to re-ingest with improved parsing
 */
import 'dotenv/config'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE!
)

async function main() {
  console.log('🗑️  Cleaning paper data...\n')
  
  // Get all papers
  const { data: papers } = await supabase
    .from('papers')
    .select('id, paper_number, year, season')
  
  if (!papers || papers.length === 0) {
    console.log('No papers to delete')
    return
  }
  
  console.log(`Found ${papers.length} paper(s):`)
  papers.forEach(p => {
    console.log(`  - ${p.year} ${p.season} Paper ${p.paper_number}`)
  })
  
  console.log('\nDeleting...')
  
  // Delete papers (cascade will delete questions, markschemes, question_topics)
  const { error } = await supabase
    .from('papers')
    .delete()
    .in('id', papers.map(p => p.id))
  
  if (error) {
    console.error('Error:', error.message)
  } else {
    console.log('✅ All papers deleted (questions, markschemes, and tags also removed via CASCADE)')
    console.log('\nYou can now re-run: npm run ingest:papers')
  }
}

main().catch(console.error)
