"use client";

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabaseBrowser';

interface AuthState {
  session?: unknown;
  sessionError?: unknown;
  user?: unknown;
  userError?: unknown;
  hasSession: boolean;
  hasUser: boolean;
  cookies: string;
  error?: string;
}

export default function AuthDebugPage() {
  const [authState, setAuthState] = useState<AuthState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      try {
        const supabase = createClient();
        
        // Get session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        
        // Get user
        const { data: { user }, error: userError } = await supabase.auth.getUser();
        
        setAuthState({
          session,
          sessionError,
          user,
          userError,
          hasSession: !!session,
          hasUser: !!user,
          cookies: document.cookie,
        });
      } catch (e) {
        setAuthState({ 
          error: String(e),
          hasSession: false,
          hasUser: false,
          cookies: document.cookie
        });
      } finally {
        setLoading(false);
      }
    }
    
    checkAuth();
  }, []);

  const signIn = async () => {
    const supabase = createClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  const signOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-xl">Loading auth state...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">🔍 Auth Debug Panel</h1>
        
        <div className="space-y-6">
          {/* Session Status */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Session Status</h2>
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className={`text-2xl ${authState?.hasSession ? '✅' : '❌'}`}>
                  {authState?.hasSession ? '✅' : '❌'}
                </span>
                <span>Has Session: {authState?.hasSession ? 'Yes' : 'No'}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-2xl ${authState?.hasUser ? '✅' : '❌'}`}>
                  {authState?.hasUser ? '✅' : '❌'}
                </span>
                <span>Has User: {authState?.hasUser ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>

          {/* User Info */}
          {authState?.user && (
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">User Information</h2>
              <div className="space-y-2 text-sm font-mono">
                <div><span className="text-gray-400">Email:</span> {(authState.user as {email?: string})?.email || 'N/A'}</div>
                <div><span className="text-gray-400">ID:</span> {(authState.user as {id?: string})?.id || 'N/A'}</div>
                <div><span className="text-gray-400">Created:</span> {(authState.user as {created_at?: string})?.created_at ? new Date((authState.user as {created_at: string}).created_at).toLocaleString() : 'N/A'}</div>
              </div>
            </div>
          )}

          {/* Session Details */}
          {authState?.session && (
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Session Details</h2>
              <div className="space-y-2 text-sm font-mono">
                <div><span className="text-gray-400">Access Token:</span> {((authState.session as {access_token?: string})?.access_token || '').substring(0, 20)}...</div>
                <div><span className="text-gray-400">Expires:</span> {(authState.session as {expires_at?: number})?.expires_at ? new Date((authState.session as {expires_at: number}).expires_at * 1000).toLocaleString() : 'N/A'}</div>
                <div><span className="text-gray-400">Provider:</span> {((authState.session as {user?: {app_metadata?: {provider?: string}}})?.user?.app_metadata?.provider) || 'N/A'}</div>
              </div>
            </div>
          )}

          {/* Cookies */}
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Browser Cookies</h2>
            <div className="text-sm font-mono break-all bg-gray-950 p-4 rounded">
              {authState?.cookies || 'No cookies found'}
            </div>
          </div>

          {/* Errors */}
          {(authState?.sessionError || authState?.userError || authState?.error) && (
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-red-400">Errors</h2>
              <pre className="text-sm overflow-auto">
                {JSON.stringify({
                  sessionError: authState.sessionError,
                  userError: authState.userError,
                  error: authState.error
                }, null, 2)}
              </pre>
            </div>
          )}

          {/* Raw State */}
          <details className="bg-gray-900 border border-gray-700 rounded-lg p-6">
            <summary className="text-xl font-semibold cursor-pointer">
              Raw Auth State (Click to expand)
            </summary>
            <pre className="mt-4 text-xs overflow-auto bg-gray-950 p-4 rounded">
              {JSON.stringify(authState, null, 2)}
            </pre>
          </details>

          {/* Actions */}
          <div className="flex gap-4">
            {!authState?.hasUser ? (
              <button
                onClick={signIn}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                Sign In with Google
              </button>
            ) : (
              <>
                <button
                  onClick={signOut}
                  className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium"
                >
                  Sign Out
                </button>
                <a
                  href="/dashboard"
                  className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium inline-block"
                >
                  Go to Dashboard
                </a>
              </>
            )}
          </div>

          {/* Instructions */}
          <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4 text-blue-400">Troubleshooting</h2>
            <ul className="space-y-2 text-sm">
              <li>✅ If you see ✅ Has Session: Yes → Auth is working!</li>
              <li>❌ If you see ❌ Has Session: No → Try signing in again</li>
              <li>🔄 If sign in fails → Check browser console (F12) for errors</li>
              <li>🍪 If no cookies → Check if cookies are enabled in browser</li>
              <li>🔗 If redirects fail → Check Supabase OAuth redirect URL settings</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
