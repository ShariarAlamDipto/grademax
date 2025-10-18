"use client"
import { createClient } from "@/lib/supabaseBrowser"
import type { User } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import SignOutButton from "./SignOutButton";

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();
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
    return <SignOutButton />;
  }
  
  return null; // Don't show sign in button on dashboard
}
