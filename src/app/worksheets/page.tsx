export default function Worksheets() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-black text-white px-6">
      <h1 className="text-5xl font-light mb-8">Worksheets</h1>
      <p className="text-lg text-gray-400 max-w-2xl text-center">
        Practice worksheets for self-study with answer keys to test your knowledge.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12 w-full max-w-5xl">
        <div className="bg-gray-900 p-6 rounded-lg shadow-lg hover:shadow-xl transition">
          <h2 className="text-xl font-semibold">Algebra Worksheets</h2>
          <p className="text-gray-400 text-sm mt-2">Practice equations & graphs</p>
        </div>
        <div className="bg-gray-900 p-6 rounded-lg shadow-lg hover:shadow-xl transition">
          <h2 className="text-xl font-semibold">Physics Problem Sets</h2>
          <p className="text-gray-400 text-sm mt-2">Kinematics, forces & energy</p>
        </div>
        <div className="bg-gray-900 p-6 rounded-lg shadow-lg hover:shadow-xl transition">
          <h2 className="text-xl font-semibold">Chemistry Exercises</h2>
          <p className="text-gray-400 text-sm mt-2">Equations, reactions & organic</p>
        </div>
      </div>
    </main>
  )
}
