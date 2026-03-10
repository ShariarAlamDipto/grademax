/**
 * Run the SQL migration to add missing columns and RLS policies
 */
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: require('path').resolve(__dirname, '..', '.env.local') });

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function main() {
  console.log('Running SQL migration...\n');

  // Step 1: Add missing columns
  console.log('Step 1: Adding pdf_url column...');
  const { error: e1 } = await supabase.rpc('exec_sql', {
    query: 'ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_url TEXT'
  }).maybeSingle();
  
  // rpc may not exist, fall back to raw REST
  if (e1) {
    console.log('RPC not available, using direct approach...');
    // Try inserting a dummy row to test if columns exist
    const { data: testRow, error: testErr } = await supabase
      .from('papers')
      .select('id, pdf_url')
      .limit(1);
    
    if (testErr && testErr.message.includes('pdf_url')) {
      console.log('pdf_url column is missing. Running migration via fetch...');
      
      // Use the Supabase REST API directly to run SQL
      const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
      
      const sqlStatements = [
        'ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_url TEXT',
        'ALTER TABLE papers ADD COLUMN IF NOT EXISTS markscheme_pdf_url TEXT',
      ];
      
      for (const sql of sqlStatements) {
        console.log(`  Executing: ${sql}`);
        const resp = await fetch(`${url}/rest/v1/rpc/`, {
          method: 'POST',
          headers: {
            'apikey': key,
            'Authorization': `Bearer ${key}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query: sql }),
        });
        if (!resp.ok) {
          console.log(`  Response: ${resp.status} - trying pg_meta...`);
        }
      }
      
      // Use the management API (pg-meta) to run SQL
      const sqlBlock = `
        ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_url TEXT;
        ALTER TABLE papers ADD COLUMN IF NOT EXISTS markscheme_pdf_url TEXT;
      `;
      
      const pgResp = await fetch(`${url}/pg/query`, {
        method: 'POST', 
        headers: {
          'apikey': key,
          'Authorization': `Bearer ${key}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: sqlBlock }),
      });
      
      if (pgResp.ok) {
        console.log('  ✓ Columns added via pg query endpoint');
      } else {
        console.log(`  pg/query returned ${pgResp.status}`);
        
        // Last resort: try the SQL endpoint used by Supabase dashboard
        const sqlResp = await fetch(`${url}/rest/v1/`, {
          method: 'POST',
          headers: {
            'apikey': key,
            'Authorization': `Bearer ${key}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=representation',
          },
          body: JSON.stringify({ query: sqlBlock }),
        });
        console.log(`  REST returned ${sqlResp.status}`);
      }
    } else if (testErr) {
      console.log('Unexpected error:', testErr.message);
    } else {
      console.log('✓ pdf_url column already exists!');
      
      // Check markscheme_pdf_url too
      const { error: msErr } = await supabase
        .from('papers')
        .select('id, markscheme_pdf_url')
        .limit(1);
      
      if (msErr && msErr.message.includes('markscheme_pdf_url')) {
        console.log('✗ markscheme_pdf_url column is missing');
      } else {
        console.log('✓ markscheme_pdf_url column already exists!');
      }
    }
  } else {
    console.log('✓ Migration ran via RPC');
  }

  // Final verification
  console.log('\n=== FINAL VERIFICATION ===');
  const { data, error } = await supabase.from('papers').select('*').limit(1);
  if (error) {
    console.log('Error:', error.message);
  } else {
    const cols = data && data.length > 0 ? Object.keys(data[0]) : [];
    console.log('Current columns:', cols);
    console.log('Has pdf_url:', cols.includes('pdf_url'));
    console.log('Has markscheme_pdf_url:', cols.includes('markscheme_pdf_url'));
    
    if (!cols.includes('pdf_url') || !cols.includes('markscheme_pdf_url')) {
      console.log('\n⚠️  COLUMNS STILL MISSING!');
      console.log('You MUST run this SQL in Supabase Dashboard > SQL Editor:');
      console.log('');
      console.log('  ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_url TEXT;');
      console.log('  ALTER TABLE papers ADD COLUMN IF NOT EXISTS markscheme_pdf_url TEXT;');
      console.log('');
      console.log('Go to: https://supabase.com/dashboard > Your Project > SQL Editor');
    } else {
      console.log('\n✅ Schema is ready! You can now run: npm run upload:papers');
    }
  }
}

main().catch(console.error);
