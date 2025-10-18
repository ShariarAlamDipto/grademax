import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import { checkAdminAuth } from '@/lib/adminAuth';

export async function GET() {
  try {
    // Check admin authentication
    const authResult = await checkAdminAuth();
    
    if (!authResult.isAdmin) {
      return NextResponse.json(
        { error: authResult.error || 'Unauthorized' },
        { status: 403 }
      );
    }
    
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    // Get all user profiles with their permissions
    const { data, error } = await supabase
      .from('user_profiles')
      .select(`
        *,
        user_permissions (*)
      `)
      .order('created_at', { ascending: false });
    
    if (error) {
      throw error;
    }
    
    return NextResponse.json({ users: data || [] });
  } catch (error) {
    console.error('Error fetching users:', error);
    return NextResponse.json(
      { error: 'Failed to fetch users' },
      { status: 500 }
    );
  }
}
