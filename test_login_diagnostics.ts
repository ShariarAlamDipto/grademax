/**
 * Login Diagnostics Test
 * 
 * Tests authentication and database setup
 */

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

async function testLogin() {
  console.log('🔐 LOGIN DIAGNOSTICS TEST\n')
  console.log('=' .repeat(80))
  
  // Step 1: Check environment variables
  console.log('\n1️⃣  Checking Environment Variables')
  console.log('─'.repeat(80))
  
  if (!supabaseUrl || !supabaseAnonKey) {
    console.error('❌ Missing environment variables!')
    console.error('   NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl ? '✓ Set' : '❌ Missing')
    console.error('   NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? '✓ Set' : '❌ Missing')
    process.exit(1)
  }
  
  console.log('✓ NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl)
  console.log('✓ NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey.substring(0, 20) + '...')
  
  // Step 2: Create client
  console.log('\n2️⃣  Creating Supabase Client')
  console.log('─'.repeat(80))
  
  const supabase = createClient(supabaseUrl, supabaseAnonKey)
  console.log('✓ Client created successfully')
  
  // Step 3: Check database connection
  console.log('\n3️⃣  Testing Database Connection')
  console.log('─'.repeat(80))
  
  try {
    const { error } = await supabase.from('profiles').select('count').limit(1)
    if (error) {
      console.error('❌ Database error:', error.message)
      if (error.message.includes('relation') || error.message.includes('does not exist')) {
        console.log('\n⚠️  Table "profiles" does not exist!')
        console.log('   Please run: COMPLETE_DATABASE_SCHEMA.sql in Supabase')
      }
    } else {
      console.log('✓ Database connection successful')
      console.log('✓ Profiles table exists')
    }
  } catch (err) {
    console.error('❌ Connection failed:', err)
  }
  
  // Step 4: Check tables exist
  console.log('\n4️⃣  Checking Required Tables')
  console.log('─'.repeat(80))
  
  const requiredTables = [
    'profiles',
    'subjects',
    'topics',
    'papers',
    'questions',
    'question_parts',
    'question_tags',
    'ingestions',
    'worksheets',
    'worksheet_items'
  ]
  
  for (const table of requiredTables) {
    try {
      const { error } = await supabase.from(table).select('count').limit(1)
      if (error) {
        console.log(`❌ ${table}: ${error.message}`)
      } else {
        console.log(`✓ ${table}: exists`)
      }
    } catch (err) {
      console.log(`❌ ${table}: error checking`)
    }
  }
  
  // Step 5: Check auth configuration
  console.log('\n5️⃣  Checking Auth Configuration')
  console.log('─'.repeat(80))
  
  try {
    const { data, error } = await supabase.auth.getSession()
    if (error) {
      console.log('⚠️  No active session (this is normal for this test)')
    } else {
      console.log('✓ Auth module working')
      if (data.session) {
        console.log('✓ Active session found!')
        console.log('  User ID:', data.session.user.id)
        console.log('  Email:', data.session.user.email)
      } else {
        console.log('ℹ️  No active session (run this after logging in)')
      }
    }
  } catch (authErr) {
    console.error('❌ Auth error:', authErr)
  }
  
  // Step 6: Test RLS policies
  console.log('\n6️⃣  Testing RLS Policies')
  console.log('─'.repeat(80))
  
  try {
    // Try to read from profiles (should work even without auth for count)
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .limit(5)
    
    if (error) {
      if (error.message.includes('RLS')) {
        console.log('✓ RLS is enabled (good!)')
        console.log('  Error:', error.message)
      } else {
        console.log('❌ Error:', error.message)
      }
    } else {
      console.log(`✓ Query successful, found ${data?.length || 0} profiles`)
      if (data && data.length > 0) {
        console.log('  Sample profile:', data[0].email || data[0].id)
      }
    }
  } catch (err) {
    console.error('❌ RLS test error:', err)
  }
  
  // Step 7: Check Google OAuth settings
  console.log('\n7️⃣  Google OAuth Configuration')
  console.log('─'.repeat(80))
  console.log('Please verify in Supabase Dashboard:')
  console.log('  1. Go to Authentication → Providers')
  console.log('  2. Google provider should be ENABLED')
  console.log('  3. Authorized redirect URIs should include:')
  console.log(`     - ${supabaseUrl}/auth/v1/callback`)
  console.log('     - http://localhost:3001/auth/callback')
  console.log('  4. Client ID and Secret from Google Cloud Console should be set')
  
  // Summary
  console.log('\n' + '='.repeat(80))
  console.log('📊 DIAGNOSTICS SUMMARY')
  console.log('='.repeat(80))
  
  console.log('\n✅ What to do next:')
  console.log('  1. If tables are missing: Run COMPLETE_DATABASE_SCHEMA.sql')
  console.log('  2. If Google OAuth not configured: Follow COMPLETE_SETUP_GUIDE.md')
  console.log('  3. Try logging in at: http://localhost:3001/login')
  console.log('  4. Check browser console for errors')
  console.log('  5. Check Network tab for failed requests')
  
  console.log('\n📝 Common Issues:')
  console.log('  - Login loop: Usually means profiles table missing or RLS issue')
  console.log('  - "relation does not exist": Run COMPLETE_DATABASE_SCHEMA.sql')
  console.log('  - OAuth error: Check Google Cloud Console settings')
  console.log('  - 401 Unauthorized: RLS policies might be too restrictive')
}

// Run diagnostics
console.log('🚀 Starting login diagnostics...\n')
testLogin().catch(err => {
  console.error('❌ Diagnostics failed:', err)
  process.exit(1)
})
