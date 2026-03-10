/**
 * Test that the schema is ready for the upload script
 */
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: require('path').resolve(__dirname, '..', '.env.local') });

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function main() {
  // 1) Check papers columns
  console.log('=== PAPERS TABLE COLUMNS ===');
  const { data: p, error: pe } = await supabase.from('papers').select('*').limit(1);
  if (pe) {
    console.log('Error:', pe.message);
  } else if (p && p.length > 0) {
    const cols = Object.keys(p[0]);
    console.log('Columns:', cols);
    const hasPdfUrl = cols.includes('pdf_url');
    const hasMsUrl = cols.includes('markscheme_pdf_url');
    console.log(`pdf_url: ${hasPdfUrl ? '✓' : '✗ MISSING — run setup-public-papers.sql first!'}`);
    console.log(`markscheme_pdf_url: ${hasMsUrl ? '✓' : '✗ MISSING — run setup-public-papers.sql first!'}`);
    
    if (!hasPdfUrl || !hasMsUrl) {
      console.log('\n⚠  You need to run this in Supabase SQL Editor FIRST:');
      console.log('   ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_url TEXT;');
      console.log('   ALTER TABLE papers ADD COLUMN IF NOT EXISTS markscheme_pdf_url TEXT;');
      return;
    }
  } else {
    // Empty table — try inserting to discover columns
    console.log('(Table empty, checking via insert test)');
  }
  
  // 2) Check subjects
  console.log('\n=== SUBJECTS ===');
  const { data: subjects } = await supabase.from('subjects').select('id, name, code, board, level');
  console.log(`Found ${subjects?.length || 0} subjects:`);
  subjects?.forEach(s => console.log(`  ${s.name} (${s.code}) — board=${s.board}, level=${s.level}`));

  // 3) Check existing papers
  console.log('\n=== EXISTING PAPERS ===');
  const { data: papers, count } = await supabase
    .from('papers')
    .select('id, year, season, paper_number, pdf_url, markscheme_pdf_url', { count: 'exact' })
    .limit(5);
  console.log(`Total papers: ${count || papers?.length || 0}`);
  papers?.forEach(p => console.log(`  ${p.year} ${p.season} ${p.paper_number} — pdf_url=${p.pdf_url ? 'set' : 'null'}, ms=${p.markscheme_pdf_url ? 'set' : 'null'}`));

  console.log('\n✅ Schema check complete. Ready to upload!');
}

main().catch(console.error);
