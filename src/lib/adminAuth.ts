import { createClient } from '@supabase/supabase-js';
import { cookies } from 'next/headers';

export async function checkAdminAuth() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  const adminEmails = process.env.ADMIN_EMAILS?.split(',').map(e => e.trim()) || [];
  
  // Get auth token from cookies
  const cookieStore = await cookies();
  const authCookie = cookieStore.get('sb-access-token') || cookieStore.get('supabase-auth-token');
  
  if (!authCookie) {
    return { isAdmin: false, error: 'Not authenticated' };
  }
  
  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: {
      headers: { Authorization: `Bearer ${authCookie.value}` },
    },
  });
  
  // Get current user
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  
  if (authError || !user) {
    return { isAdmin: false, error: 'Not authenticated' };
  }
  
  // Check if user email is in admin list
  const isAdmin = adminEmails.includes(user.email || '');
  
  if (!isAdmin) {
    return { isAdmin: false, error: 'Unauthorized - Admin access only' };
  }
  
  return { isAdmin: true, user };
}
