"use client"
import { supabase } from "@/lib/supabaseClient"


import type { User } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getUser();
      setUser(data?.user || null);
    };
    getUser();
    const { data: listener } = supabase.auth.onAuthStateChange(() => getUser());
    return () => { listener?.subscription?.unsubscribe?.(); };
  }, []);

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
  return (
    <button
      className="rounded-md bg-blue-500 px-3 py-1.5 text-sm text-white hover:bg-blue-600"
      onClick={() => window.location.href = "/login"}
    >
      Sign in
    </button>
  );
}
