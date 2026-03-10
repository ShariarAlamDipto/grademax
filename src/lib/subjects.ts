export type Level = "igcse" | "ial"

export type Subject = {
  slug: string
  name: string
  level: Level
  colorKey: "physics" | "maths" | "biology" | "chemistry" | "ict" | "english" | "other"
  /** If this subject has past papers in the raw data, this is the folder name */
  dataFolder?: string
}

export const subjectColorClasses: Record<Subject["colorKey"], string> = {
  physics:   "bg-orange-500/15 text-orange-200 ring-1 ring-orange-400/30 hover:bg-orange-400/20",
  maths:     "bg-sky-500/15 text-sky-200 ring-1 ring-sky-400/30 hover:bg-sky-400/20",
  biology:   "bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-400/30 hover:bg-emerald-400/20",
  chemistry: "bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/30 hover:bg-violet-400/20",
  ict:       "bg-red-500/15 text-red-200 ring-1 ring-red-400/30 hover:bg-red-400/20",
  english:   "bg-rose-500/15 text-rose-200 ring-1 ring-rose-400/30 hover:bg-rose-400/20",
  other:     "bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-400/30 hover:bg-indigo-400/20",
}

export const subjects: Subject[] = [
  // ─── IGCSE ────────────────────────────────────────────────────────────────
  { slug: "physics",              name: "Physics",                  level: "igcse", colorKey: "physics",   dataFolder: "Physics" },
  { slug: "chemistry",            name: "Chemistry",                level: "igcse", colorKey: "chemistry", dataFolder: "Chemistry" },
  { slug: "biology",              name: "Biology",                  level: "igcse", colorKey: "biology",   dataFolder: "Biology" },
  { slug: "human-biology",        name: "Human Biology",            level: "igcse", colorKey: "biology",   dataFolder: "Human Biology" },
  { slug: "maths-a",              name: "Mathematics A",            level: "igcse", colorKey: "maths",     dataFolder: "Mathematics_A" },
  { slug: "maths-b",              name: "Mathematics B",            level: "igcse", colorKey: "maths",     dataFolder: "Mathematics_B" },
  { slug: "further-pure-maths",   name: "Further Pure Mathematics", level: "igcse", colorKey: "maths",     dataFolder: "Further Pure Maths" },
  { slug: "english-language-a",   name: "English Language A",       level: "igcse", colorKey: "english",   dataFolder: "English_A" },
  { slug: "english-language-b",   name: "English Language B",       level: "igcse", colorKey: "english",   dataFolder: "English_B" },
  { slug: "ict",                  name: "ICT",                      level: "igcse", colorKey: "ict",       dataFolder: "ICT" },
  { slug: "accounting",           name: "Accounting",               level: "igcse", colorKey: "other",     dataFolder: "Accounting" },
  { slug: "business",             name: "Business",                 level: "igcse", colorKey: "other",     dataFolder: "Business" },
  { slug: "commerce",             name: "Commerce",                 level: "igcse", colorKey: "other",     dataFolder: "Commerce" },
  { slug: "economics",            name: "Economics",                level: "igcse", colorKey: "other",     dataFolder: "Economics" },
  { slug: "bangla",               name: "Bangla",                   level: "igcse", colorKey: "other",     dataFolder: "Bangla" },

  // ─── IAL ──────────────────────────────────────────────────────────────────
  { slug: "mechanics-1",          name: "Mechanics 1 (M1)",         level: "ial",   colorKey: "other",     dataFolder: "Mechanics_1" },
  { slug: "pure-mathematics-1",   name: "Pure Mathematics 1 (P1)",  level: "ial",   colorKey: "maths" },
  { slug: "pure-mathematics-2",   name: "Pure Mathematics 2 (P2)",  level: "ial",   colorKey: "maths" },
  { slug: "pure-mathematics-3",   name: "Pure Mathematics 3 (P3)",  level: "ial",   colorKey: "maths" },
  { slug: "pure-mathematics-4",   name: "Pure Mathematics 4 (P4)",  level: "ial",   colorKey: "maths" },
  { slug: "statistics-1",         name: "Statistics 1 (S1)",        level: "ial",   colorKey: "other" },
  { slug: "physics-ial",          name: "Physics",                  level: "ial",   colorKey: "physics" },
]

/** Subjects that have past papers available for download */
export const pastPaperSubjects = subjects.filter(s => !!s.dataFolder)

/** Find a subject by its URL slug */
export function getSubjectBySlug(slug: string): Subject | undefined {
  return subjects.find(s => s.slug === slug)
}

export const byLevel = (level: Level) => subjects.filter(s => s.level === level)
export const findSubject = (level: Level, slug: string) =>
  subjects.find(s => s.level === level && s.slug === slug) || null
