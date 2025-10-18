import { NextResponse } from 'next/server';

/**
 * Diagnostic endpoint to check API configuration
 * Returns info about environment variables and API connectivity
 */
export async function GET() {
  const diagnostics = {
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
    hasSupabaseUrl: !!process.env.NEXT_PUBLIC_SUPABASE_URL,
    hasAnonKey: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    hasServiceKey: !!process.env.SUPABASE_SERVICE_ROLE_KEY,
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ? 
      process.env.NEXT_PUBLIC_SUPABASE_URL.substring(0, 30) + '...' : 
      'MISSING',
  };

  // Test Supabase connection
  if (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    try {
      const { createClient } = await import('@supabase/supabase-js');
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
      );
      
      // Try to fetch subjects
      const { data: subjects, error: subjectsError } = await supabase
        .from('subjects')
        .select('id, name, code')
        .limit(5);
      
      // Try to fetch topics
      const { data: topics, error: topicsError } = await supabase
        .from('topics')
        .select('id, name, code')
        .limit(5);

      return NextResponse.json({
        ...diagnostics,
        supabaseConnected: true,
        subjectsTest: {
          success: !subjectsError,
          count: subjects?.length || 0,
          error: subjectsError?.message,
          sample: subjects?.[0],
        },
        topicsTest: {
          success: !topicsError,
          count: topics?.length || 0,
          error: topicsError?.message,
          sample: topics?.[0],
        },
      });
    } catch (err) {
      return NextResponse.json({
        ...diagnostics,
        supabaseConnected: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  return NextResponse.json({
    ...diagnostics,
    supabaseConnected: false,
    error: 'Missing Supabase credentials',
  });
}
