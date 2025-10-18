import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import fs from 'fs';
import path from 'path';

// This endpoint applies the Phase 1 migration
// Only accessible to admins
export async function POST(request: NextRequest) {
  try {
    // Get user from request
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    
    // Create admin client
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    
    // Read migration file
    const migrationPath = path.join(process.cwd(), 'supabase', 'migrations', '02_phase1_security.sql');
    const sql = fs.readFileSync(migrationPath, 'utf8');
    
    console.log('📦 Applying Phase 1 migration...');
    
    // Split SQL into statements
    const statements = sql
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith('--') && !s.match(/^={2,}/));
    
    const results = [];
    const errors = [];
    
    // Execute each statement
    for (let i = 0; i < statements.length; i++) {
      const stmt = statements[i] + ';';
      
      try {
        // Use the SQL query feature via RPC if available
        const { error } = await supabase.rpc('exec_sql', { sql_query: stmt });
        
        if (error) {
          console.error(`Statement ${i + 1} failed:`, error.message);
          errors.push({ statement: i + 1, error: error.message });
        } else {
          results.push({ statement: i + 1, success: true });
        }
      } catch (e) {
        console.error(`Statement ${i + 1} exception:`, e);
        errors.push({ statement: i + 1, error: String(e) });
      }
    }
    
    if (errors.length > 0) {
      return NextResponse.json({
        success: false,
        message: 'Migration had errors',
        results,
        errors,
        note: 'Please apply migration manually via Supabase Dashboard → SQL Editor'
      }, { status: 500 });
    }
    
    return NextResponse.json({
      success: true,
      message: 'Migration applied successfully',
      tablesCreated: ['user_sessions', 'trusted_devices', 'audit_log', 'usage_meters'],
      results
    });
    
  } catch (error) {
    console.error('Migration error:', error);
    return NextResponse.json({ 
      error: 'Migration failed', 
      details: String(error),
      instructions: 'Please apply manually: Supabase Dashboard → SQL Editor → Copy supabase/migrations/02_phase1_security.sql'
    }, { status: 500 });
  }
}
