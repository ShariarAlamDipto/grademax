// Test Supabase connection and check data
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://tybaetnvnfgniotdfxze.supabase.co';
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5YmFldG52bmZnbmlvdGRmeHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwOTkzMTcsImV4cCI6MjA3MjY3NTMxN30.QRxEmsZFtp0LHFycU6pljuFqJineV8AcTpjo4nBAYes';

const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function testConnection() {
  console.log('🔍 Testing Supabase Connection...\n');

  // Test 1: Check subjects
  console.log('📚 TEST 1: Checking subjects table...');
  const { data: subjects, error: subjectsError } = await supabase
    .from('subjects')
    .select('id, code, name, level')
    .order('code');

  if (subjectsError) {
    console.error('❌ Error fetching subjects:', subjectsError.message);
  } else {
    console.log(`✅ Found ${subjects?.length || 0} subjects`);
    if (subjects && subjects.length > 0) {
      console.log('First few subjects:');
      subjects.slice(0, 5).forEach(s => {
        console.log(`  - ${s.level} ${s.name} (${s.code}) [ID: ${s.id}]`);
      });
    }
  }

  // Test 2: Check Physics subject specifically
  console.log('\n🔬 TEST 2: Checking Physics subject...');
  const { data: physics, error: physicsError } = await supabase
    .from('subjects')
    .select('id, code, name, level')
    .eq('code', '4PH1')
    .eq('level', 'IGCSE')
    .single();

  if (physicsError) {
    console.error('❌ Error fetching Physics:', physicsError.message);
  } else if (physics) {
    console.log(`✅ Found Physics: ${physics.level} ${physics.name} (${physics.code})`);
    console.log(`   ID: ${physics.id}`);

    // Test 3: Check topics for Physics
    console.log('\n📖 TEST 3: Checking Physics topics...');
    const { data: topics, error: topicsError } = await supabase
      .from('topics')
      .select('id, code, name, spec_ref')
      .eq('subject_id', physics.id)
      .order('code');

    if (topicsError) {
      console.error('❌ Error fetching topics:', topicsError.message);
    } else {
      console.log(`✅ Found ${topics?.length || 0} Physics topics`);
      if (topics && topics.length > 0) {
        console.log('Topics:');
        topics.forEach(t => {
          console.log(`  - ${t.code}: ${t.name} (${t.spec_ref})`);
        });
      } else {
        console.log('⚠️  NO TOPICS FOUND! You need to run COMPLETE_FIX.sql');
      }
    }
  } else {
    console.log('⚠️  Physics subject not found!');
  }

  // Test 4: Check topics table structure
  console.log('\n🏗️  TEST 4: Checking topics table structure...');
  const { data: topicsCount, error: countError } = await supabase
    .from('topics')
    .select('id', { count: 'exact', head: true });

  if (countError) {
    console.error('❌ Error checking topics table:', countError.message);
  } else {
    console.log(`✅ Topics table exists`);
  }

  // Test 5: Check profiles table
  console.log('\n👤 TEST 5: Checking profiles table...');
  const { data: profiles, error: profilesError } = await supabase
    .from('profiles')
    .select('id, email')
    .limit(1);

  if (profilesError) {
    console.error('❌ Error fetching profiles:', profilesError.message);
    console.log('⚠️  Profiles table might not exist! Run COMPLETE_FIX.sql');
  } else {
    console.log(`✅ Profiles table exists with ${profiles?.length || 0} profiles`);
  }

  console.log('\n' + '='.repeat(60));
  console.log('✅ DIAGNOSIS COMPLETE');
  console.log('='.repeat(60));
}

testConnection().catch(console.error);
