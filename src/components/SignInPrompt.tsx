import Link from 'next/link';

interface SignInPromptProps {
  /** Headline, e.g. "Sign in to make customised test papers". */
  title: string;
  /** Page to come back to after signing in. */
  next: string;
}

/**
 * Shown in place of the raw 401 error when a signed-out visitor uses a tool
 * whose API needs an account (test builder, worksheet generator).
 */
export default function SignInPrompt({ title, next }: SignInPromptProps) {
  return (
    <div className="bg-blue-950/70 border border-blue-500/60 rounded-xl p-4 md:p-6 mb-4 md:mb-8 text-center">
      <p className="font-bold text-white text-base md:text-lg mb-1">{title}</p>
      <p className="text-blue-200 text-sm mb-4">
        It&apos;s free — create an account or sign in to continue.
      </p>
      <Link
        href={`/login?next=${encodeURIComponent(next)}`}
        className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2.5 rounded-lg transition-colors"
      >
        Sign in
      </Link>
    </div>
  );
}
