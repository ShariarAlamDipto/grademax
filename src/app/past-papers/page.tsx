import { supabase } from '../../lib/supabaseClient'

export default async function PastPapers() {
  type Subject = {
    name: string;
    level: string;
  };
  type Paper = {
    id: number;
    year: number;
    paper_type: string;
    file_url: string;
    subjects: Subject[];
  };
  const { data: papers, error } = await supabase
    .from('papers')
    .select('id, year, paper_type, file_url, subjects(name, level)')

  if (error) {
    console.error(error)
    return <p className="text-red-500">Error loading papers</p>
  }

  return (
    <main className="min-h-screen bg-black text-white p-8">
      <h1 className="text-4xl mb-8">Past Papers</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {papers?.map((paper: Paper) => (
          <div key={paper.id} className="bg-gray-900 p-6 rounded-lg shadow">
            {Array.isArray(paper.subjects) && paper.subjects.length > 0 ? (
              <h2 className="text-xl font-semibold">
                {paper.subjects[0].name} ({paper.subjects[0].level})
              </h2>
            ) : (
              <h2 className="text-xl font-semibold">Unknown Subject</h2>
            )}
            <p className="text-gray-400">{paper.year} — {paper.paper_type}</p>
            <a
              href={paper.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:underline mt-2 inline-block"
            >
              View Paper
            </a>
          </div>
        ))}
      </div>
    </main>
  )
}
