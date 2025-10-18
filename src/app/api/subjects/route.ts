import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

export async function GET() {
  try {
    const { data, error } = await supabase
      .from('subjects')
      .select('id, name, code, level, color')
      .order('name')
    
    if (error) {
      console.error('Subjects API error:', error)
      return NextResponse.json([], { status: 200 }) // Return empty array on error
    }
    
    return NextResponse.json(data || [], { status: 200 })
  } catch (err) {
    console.error('Subjects API exception:', err)
    return NextResponse.json([], { status: 200 }) // Return empty array on exception
  }
}
