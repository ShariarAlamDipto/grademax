import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import { checkAdminAuth } from '@/lib/adminAuth';

export async function GET(request: Request) {
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
    
    const { searchParams } = new URL(request.url);
    const userId = searchParams.get('userId');
    const limit = parseInt(searchParams.get('limit') || '50');
    
    let query = supabase
      .from('worksheet_generation_logs')
      .select('*')
      .order('generated_at', { ascending: false })
      .limit(limit);
    
    if (userId) {
      query = query.eq('user_id', userId);
    }
    
    const { data, error } = await query;
    
    if (error) {
      throw error;
    }
    
    return NextResponse.json({ logs: data || [] });
  } catch (error) {
    console.error('Error fetching logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch logs' },
      { status: 500 }
    );
  }
}
