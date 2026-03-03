import { NextResponse } from "next/server"

// Debug endpoint to verify which env vars are available on Vercel
// Does NOT expose values — only shows whether each var is set
export async function GET() {
  return NextResponse.json({
    env: {
      NEXT_PUBLIC_SUPABASE_URL: !!process.env.NEXT_PUBLIC_SUPABASE_URL,
      NEXT_PUBLIC_SUPABASE_ANON_KEY: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      SUPABASE_SERVICE_ROLE_KEY: !!process.env.SUPABASE_SERVICE_ROLE_KEY,
      NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY: !!process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY,
      SUPABASE_SERVICE_KEY: !!process.env.SUPABASE_SERVICE_KEY,
      NODE_ENV: process.env.NODE_ENV,
      VERCEL: !!process.env.VERCEL,
      VERCEL_ENV: process.env.VERCEL_ENV || "not-set",
    },
    timestamp: new Date().toISOString(),
  })
}
