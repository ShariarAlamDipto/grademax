import { getSupabaseServer } from '@/lib/supabaseServer';
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET() {
  try {
    const cookieStore = await cookies();
    const allCookies = cookieStore.getAll();
    
    const supabase = getSupabaseServer();
    
    // Try to get user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();
    
    return NextResponse.json({
      cookies: allCookies.map(c => ({ name: c.name, hasValue: !!c.value, valueLength: c.value?.length || 0 })),
      hasUser: !!user,
      hasSession: !!session,
      userId: user?.id || null,
      userEmail: user?.email || null,
      authError: authError?.message || null,
      sessionError: sessionError?.message || null,
      timestamp: new Date().toISOString()
    });
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json({
      error: err.message,
      stack: err.stack
    }, { status: 500 });
  }
}
