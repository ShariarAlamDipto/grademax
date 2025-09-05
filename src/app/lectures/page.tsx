export default function Lectures() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white px-6">
      <h1 className="text-5xl font-light mb-8">Lectures</h1>
      <p className="text-lg text-gray-400 max-w-2xl text-center">
        Access lecture notes, recorded sessions, and study guides prepared for O-Level, A-Level, and IGCSE.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12 w-full max-w-4xl">
        <div className="bg-gray-900 p-6 rounded-lg shadow-lg hover:shadow-xl transition">
          <h2 className="text-xl font-semibold">Mathematics Lectures</h2>
          <p className="text-gray-400 text-sm mt-2">Step-by-step explanations</p>
        </div>
        <div className="bg-gray-900 p-6 rounded-lg shadow-lg hover:shadow-xl transition">
          <h2 className="text-xl font-semibold">Biology Lectures</h2>
          <p className="text-gray-400 text-sm mt-2">Key concepts with examples</p>
        </div>
      </div>
    </main>
  )
}
