import { getSupabaseServer } from '@/lib/supabaseServer';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const supabase = getSupabaseServer();
    
    console.log('[check-permission] Checking user permission...');
    
    // Get current user
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    
    if (authError || !user) {
      console.log('[check-permission] Not authenticated:', authError?.message);
      return NextResponse.json(
        { hasPermission: false, error: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    console.log('[check-permission] User authenticated:', user.email);
    
    // Check user permissions
    const { data: permission, error: permError } = await supabase
      .from('user_permissions')
      .select('can_generate_worksheets, is_active, max_worksheets_per_day')
      .eq('user_id', user.id)
      .single();
    
    if (permError) {
      console.log('[check-permission] No permission record found:', permError.message);
      // User doesn't have permission record yet
      return NextResponse.json({
        hasPermission: false,
        error: 'No permissions configured',
        needsApproval: true,
      });
    }
    
    console.log('[check-permission] Permission record:', permission);
    
    if (!permission.can_generate_worksheets || !permission.is_active) {
      console.log('[check-permission] Permission denied');
      return NextResponse.json({
        hasPermission: false,
        error: 'Worksheet generation permission not granted',
        needsApproval: true,
      });
    }
    
    // Check daily quota if set
    let remainingQuota: number | null = null;
    if (permission.max_worksheets_per_day) {
      const { data: quotaResult } = await supabase
        .rpc('get_remaining_worksheet_quota', { check_user_id: user.id });
      
      remainingQuota = quotaResult;
      console.log('[check-permission] Remaining quota:', remainingQuota);
      
      if (remainingQuota !== null && remainingQuota <= 0) {
        console.log('[check-permission] Quota exceeded');
        return NextResponse.json({
          hasPermission: false,
          error: 'Daily worksheet quota exceeded',
          quotaExceeded: true,
          maxPerDay: permission.max_worksheets_per_day,
        });
      }
    }
    
    // User has permission
    console.log('[check-permission] Permission granted');
    return NextResponse.json({
      hasPermission: true,
      remainingQuota: remainingQuota,
      maxPerDay: permission.max_worksheets_per_day,
    });
    
  } catch (error) {
    console.error('Permission check error:', error);
    return NextResponse.json(
      { hasPermission: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
