"use client";
import { supabase } from "@/lib/supabaseClient";
import { useCallback } from "react";

export default function LoginPage() {
  const signIn = useCallback(async () => {
    const origin = window.location.origin;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${origin}/dashboard` },
    });
  }, []);

  return (
    <main className="min-h-screen bg-black text-white grid place-items-center p-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 max-w-sm w-full text-center">
        <h1 className="text-2xl font-semibold mb-4">Sign in to GradeMax</h1>
        <button
          onClick={signIn}
          className="w-full rounded-lg bg-white text-black py-2 font-medium hover:opacity-90"
        >
          Continue with Google
        </button>
      </div>
    </main>
  );
}

