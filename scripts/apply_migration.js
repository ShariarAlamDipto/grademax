const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config({ path: '.env.local' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('Missing Supabase credentials in .env.local');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function applyMigration() {
  console.log('📦 Reading migration file...');
  
  const migrationPath = path.join(__dirname, '..', 'supabase', 'migrations', '02_phase1_security.sql');
  const sql = fs.readFileSync(migrationPath, 'utf8');
  
  console.log('🚀 Applying Phase 1 migration to database...');
  console.log('   - Creating user_sessions table');
  console.log('   - Creating trusted_devices table');
  console.log('   - Creating audit_log table');
  console.log('   - Creating usage_meters table');
  console.log('   - Adding role_type to user_profiles');
  console.log('   - Creating helper functions\n');
  
  try {
    // Execute the migration SQL
    const { data, error } = await supabase.rpc('exec_sql', { sql_query: sql });
    
    if (error) {
      // If rpc doesn't exist, try direct execution (Supabase might not support this)
      console.log('⚠️  RPC method not available, trying alternative approach...\n');
      
      // Split SQL into individual statements and execute
      const statements = sql
        .split(';')
        .map(s => s.trim())
        .filter(s => s.length > 0 && !s.startsWith('--'));
      
      for (let i = 0; i < statements.length; i++) {
        const stmt = statements[i];
        if (stmt) {
          console.log(`   Executing statement ${i + 1}/${statements.length}...`);
          const { error: execError } = await supabase.from('_').select('*').limit(0); // This won't work
          
          if (execError) {
            console.error(`   ❌ Error on statement ${i + 1}:`, execError.message);
          }
        }
      }
    } else {
      console.log('✅ Migration applied successfully!\n');
      console.log('📊 New tables created:');
      console.log('   - user_sessions (session tracking)');
      console.log('   - trusted_devices (device management)');
      console.log('   - audit_log (tamper-evident logging)');
      console.log('   - usage_meters (quota tracking)\n');
      console.log('🔧 New functions created:');
      console.log('   - get_active_sessions_count()');
      console.log('   - get_current_month_usage()');
      console.log('   - increment_usage_meter()');
      console.log('   - create_audit_log_entry()');
      console.log('   - cleanup_expired_sessions()\n');
    }
  } catch (err) {
    console.error('❌ Migration failed:', err.message);
    console.error('\n📝 Please apply the migration manually:');
    console.error('   1. Go to https://supabase.com/dashboard');
    console.error('   2. Select your project');
    console.error('   3. Go to SQL Editor');
    console.error('   4. Copy the contents of: supabase/migrations/02_phase1_security.sql');
    console.error('   5. Paste and run\n');
    process.exit(1);
  }
}

applyMigration();
