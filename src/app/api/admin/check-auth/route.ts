import { getSupabaseServer } from '@/lib/supabaseServer';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const adminEmails = process.env.ADMIN_EMAILS?.split(',').map(e => e.trim()) || [];
    
    const supabase = getSupabaseServer();
    
    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      return NextResponse.json(
        { error: 'Not authenticated', isAdmin: false },
        { status: 401 }
      );
    }
    
    // Check if user email is in admin list
    const isAdmin = adminEmails.includes(user.email || '');
    
    if (!isAdmin) {
      return NextResponse.json(
        { error: 'Unauthorized - Admin access only', isAdmin: false },
        { status: 403 }
      );
    }
    
    // User is admin
    return NextResponse.json({ 
      isAdmin: true,
      email: user.email,
      message: 'Admin access granted'
    });
    
  } catch (error) {
    console.error('Error checking admin auth:', error);
    return NextResponse.json(
      { error: 'Internal server error', isAdmin: false },
      { status: 500 }
    );
  }
}
