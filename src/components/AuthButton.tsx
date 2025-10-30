"use client"
import { supabase } from "@/lib/supabaseClient"
import type { User } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getUser();
      setUser(data?.user || null);
      setLoading(false);
    };
    getUser();
    const { data: listener } = supabase.auth.onAuthStateChange(() => getUser());
    return () => { listener?.subscription?.unsubscribe?.(); };
  }, []);

  // Don't show anything while loading
  if (loading) {
    return null;
  }

  if (user) {
    return (
      <button
        className="rounded-md bg-white/10 px-3 py-1.5 text-sm hover:bg-white/15"
        onClick={() => supabase.auth.signOut().then(() => (window.location.href = "/"))}
      >
        Sign out
      </button>
    );
  }
  
  return null; // Don't show sign in button on dashboard
}
