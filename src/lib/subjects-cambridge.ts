import type { Subject } from "./subjects"

/**
 * Cambridge (CAIE) subjects with hosted past papers.
 *
 * Only content-verified subjects are listed. The scraper misfiled many
 * minor subjects (front-page syllabus code disagrees with the folder), so this
 * list must stay in sync with VERIFIED_SUBJECTS in
 * scripts/ingest_cambridge_papers.py.
 *
 * `name` is the display name; `dbName` is the Supabase subjects.name key
 * (board-prefixed — Edexcel already owns the bare names). `dataFolder` is the
 * scraper-tree folder and the R2 key segment. `examCode` is the primary
 * Cambridge syllabus code, shown to students as "{examCode}/{component}".
 */
export const cambridgeSubjects: Subject[] = [
  // ─── Cambridge IGCSE ──────────────────────────────────────────────────────
  { slug: "cambridge-igcse-accounting", name: "Accounting", level: "cambridge-igcse", colorKey: "other", dataFolder: "Accounting", dbName: "Cambridge IGCSE Accounting", examCode: "0452" },
  { slug: "cambridge-igcse-additional-mathematics", name: "Additional Mathematics", level: "cambridge-igcse", colorKey: "maths", dataFolder: "Additional_Mathematics", dbName: "Cambridge IGCSE Additional Mathematics", examCode: "0606" },
  { slug: "cambridge-igcse-afrikaans-second-language", name: "Afrikaans Second Language", level: "cambridge-igcse", colorKey: "other", dataFolder: "Afrikaans_Second_Language", dbName: "Cambridge IGCSE Afrikaans Second Language", examCode: "0548" },
  { slug: "cambridge-igcse-art-and-design", name: "Art and Design", level: "cambridge-igcse", colorKey: "other", dataFolder: "Art_and_Design", dbName: "Cambridge IGCSE Art and Design", examCode: "0400" },
  { slug: "cambridge-igcse-biology", name: "Biology", level: "cambridge-igcse", colorKey: "biology", dataFolder: "Biology", dbName: "Cambridge IGCSE Biology", examCode: "0610" },
  { slug: "cambridge-igcse-business-studies", name: "Business Studies", level: "cambridge-igcse", colorKey: "other", dataFolder: "Business_Studies", dbName: "Cambridge IGCSE Business Studies", examCode: "0450" },
  { slug: "cambridge-igcse-chemistry", name: "Chemistry", level: "cambridge-igcse", colorKey: "chemistry", dataFolder: "Chemistry", dbName: "Cambridge IGCSE Chemistry", examCode: "0620" },
  { slug: "cambridge-igcse-chinese-first-language", name: "Chinese First Language", level: "cambridge-igcse", colorKey: "other", dataFolder: "Chinese_First_Language", dbName: "Cambridge IGCSE Chinese First Language", examCode: "0509" },
  { slug: "cambridge-igcse-co-ordinated-sciences", name: "Co-ordinated Sciences", level: "cambridge-igcse", colorKey: "biology", dataFolder: "Co-ordinated_Sciences", dbName: "Cambridge IGCSE Co-ordinated Sciences", examCode: "0654" },
  { slug: "cambridge-igcse-combined-science", name: "Combined Science", level: "cambridge-igcse", colorKey: "biology", dataFolder: "Combined_Science", dbName: "Cambridge IGCSE Combined Science", examCode: "0653" },
  { slug: "cambridge-igcse-computer-science", name: "Computer Science", level: "cambridge-igcse", colorKey: "biology", dataFolder: "Computer_Science", dbName: "Cambridge IGCSE Computer Science", examCode: "0478" },
  { slug: "cambridge-igcse-design-and-technology", name: "Design and Technology", level: "cambridge-igcse", colorKey: "other", dataFolder: "Design_and_Technology", dbName: "Cambridge IGCSE Design and Technology", examCode: "0445" },
  { slug: "cambridge-igcse-economics", name: "Economics", level: "cambridge-igcse", colorKey: "other", dataFolder: "Economics", dbName: "Cambridge IGCSE Economics", examCode: "0455" },
  { slug: "cambridge-igcse-english-first-language", name: "English First Language", level: "cambridge-igcse", colorKey: "english", dataFolder: "English_First_Language", dbName: "Cambridge IGCSE English First Language", examCode: "0500" },
  { slug: "cambridge-igcse-english-literature", name: "English Literature", level: "cambridge-igcse", colorKey: "english", dataFolder: "English_Literature", dbName: "Cambridge IGCSE English Literature", examCode: "0475" },
  { slug: "cambridge-igcse-english-second-language", name: "English Second Language", level: "cambridge-igcse", colorKey: "english", dataFolder: "English_Second_Language", dbName: "Cambridge IGCSE English Second Language", examCode: "0510" },
  { slug: "cambridge-igcse-environmental-management", name: "Environmental Management", level: "cambridge-igcse", colorKey: "biology", dataFolder: "Environmental_Management", dbName: "Cambridge IGCSE Environmental Management", examCode: "0680" },
  { slug: "cambridge-igcse-french", name: "French", level: "cambridge-igcse", colorKey: "other", dataFolder: "French", dbName: "Cambridge IGCSE French", examCode: "0520" },
  { slug: "cambridge-igcse-geography", name: "Geography", level: "cambridge-igcse", colorKey: "other", dataFolder: "Geography", dbName: "Cambridge IGCSE Geography", examCode: "0460" },
  { slug: "cambridge-igcse-german", name: "German", level: "cambridge-igcse", colorKey: "other", dataFolder: "German", dbName: "Cambridge IGCSE German", examCode: "0525" },
  { slug: "cambridge-igcse-global-perspectives", name: "Global Perspectives", level: "cambridge-igcse", colorKey: "other", dataFolder: "Global_Perspectives", dbName: "Cambridge IGCSE Global Perspectives", examCode: "0457" },
  { slug: "cambridge-igcse-history", name: "History", level: "cambridge-igcse", colorKey: "other", dataFolder: "History", dbName: "Cambridge IGCSE History", examCode: "0470" },
  { slug: "cambridge-igcse-ict", name: "ICT", level: "cambridge-igcse", colorKey: "ict", dataFolder: "ICT", dbName: "Cambridge IGCSE ICT", examCode: "0417" },
  { slug: "cambridge-igcse-international-mathematics", name: "International Mathematics", level: "cambridge-igcse", colorKey: "maths", dataFolder: "International_Mathematics", dbName: "Cambridge IGCSE International Mathematics", examCode: "0607" },
  { slug: "cambridge-igcse-malay-first-language", name: "Malay First Language", level: "cambridge-igcse", colorKey: "other", dataFolder: "Malay_First_Language", dbName: "Cambridge IGCSE Malay First Language", examCode: "0696" },
  { slug: "cambridge-igcse-malay-second-language", name: "Malay Second Language", level: "cambridge-igcse", colorKey: "other", dataFolder: "Malay_Second_Language", dbName: "Cambridge IGCSE Malay Second Language", examCode: "0546" },
  { slug: "cambridge-igcse-mathematics", name: "Mathematics", level: "cambridge-igcse", colorKey: "maths", dataFolder: "Mathematics", dbName: "Cambridge IGCSE Mathematics", examCode: "0580" },
  { slug: "cambridge-igcse-physics", name: "Physics", level: "cambridge-igcse", colorKey: "physics", dataFolder: "Physics", dbName: "Cambridge IGCSE Physics", examCode: "0625" },
  { slug: "cambridge-igcse-religious-studies", name: "Religious Studies", level: "cambridge-igcse", colorKey: "other", dataFolder: "Religious_Studies", dbName: "Cambridge IGCSE Religious Studies", examCode: "0490" },
  { slug: "cambridge-igcse-spanish-first-language", name: "Spanish First Language", level: "cambridge-igcse", colorKey: "other", dataFolder: "Spanish_First_Language", dbName: "Cambridge IGCSE Spanish First Language", examCode: "0502" },
  { slug: "cambridge-igcse-travel-and-tourism", name: "Travel and Tourism", level: "cambridge-igcse", colorKey: "other", dataFolder: "Travel_and_Tourism", dbName: "Cambridge IGCSE Travel and Tourism", examCode: "0471" },

  // ─── Cambridge International A Level ──────────────────────────────────────
  { slug: "cambridge-a-level-accounting", name: "Accounting", level: "cambridge-a-level", colorKey: "other", dataFolder: "Accounting", dbName: "Cambridge A Level Accounting", examCode: "9706" },
  { slug: "cambridge-a-level-biology", name: "Biology", level: "cambridge-a-level", colorKey: "biology", dataFolder: "Biology", dbName: "Cambridge A Level Biology", examCode: "9700" },
  { slug: "cambridge-a-level-business", name: "Business", level: "cambridge-a-level", colorKey: "other", dataFolder: "Business", dbName: "Cambridge A Level Business", examCode: "9609" },
  { slug: "cambridge-a-level-chemistry", name: "Chemistry", level: "cambridge-a-level", colorKey: "chemistry", dataFolder: "Chemistry", dbName: "Cambridge A Level Chemistry", examCode: "9701" },
  { slug: "cambridge-a-level-computer-science", name: "Computer Science", level: "cambridge-a-level", colorKey: "biology", dataFolder: "Computer_Science", dbName: "Cambridge A Level Computer Science", examCode: "9608" },
  { slug: "cambridge-a-level-economics", name: "Economics", level: "cambridge-a-level", colorKey: "other", dataFolder: "Economics", dbName: "Cambridge A Level Economics", examCode: "9708" },
  { slug: "cambridge-a-level-english-language", name: "English Language", level: "cambridge-a-level", colorKey: "english", dataFolder: "English_Language", dbName: "Cambridge A Level English Language", examCode: "9093" },
  { slug: "cambridge-a-level-english-literature", name: "English Literature", level: "cambridge-a-level", colorKey: "english", dataFolder: "English_Literature", dbName: "Cambridge A Level English Literature", examCode: "9695" },
  { slug: "cambridge-a-level-further-mathematics", name: "Further Mathematics", level: "cambridge-a-level", colorKey: "maths", dataFolder: "Further_Mathematics", dbName: "Cambridge A Level Further Mathematics", examCode: "9231" },
  { slug: "cambridge-a-level-geography", name: "Geography", level: "cambridge-a-level", colorKey: "other", dataFolder: "Geography", dbName: "Cambridge A Level Geography", examCode: "9696" },
  { slug: "cambridge-a-level-history", name: "History", level: "cambridge-a-level", colorKey: "other", dataFolder: "History", dbName: "Cambridge A Level History", examCode: "9389" },
  { slug: "cambridge-a-level-information-technology", name: "Information Technology", level: "cambridge-a-level", colorKey: "ict", dataFolder: "Information_Technology", dbName: "Cambridge A Level Information Technology", examCode: "9626" },
  { slug: "cambridge-a-level-law", name: "Law", level: "cambridge-a-level", colorKey: "other", dataFolder: "Law", dbName: "Cambridge A Level Law", examCode: "9084" },
  { slug: "cambridge-a-level-mathematics", name: "Mathematics", level: "cambridge-a-level", colorKey: "maths", dataFolder: "Mathematics", dbName: "Cambridge A Level Mathematics", examCode: "9709" },
  { slug: "cambridge-a-level-physics", name: "Physics", level: "cambridge-a-level", colorKey: "physics", dataFolder: "Physics", dbName: "Cambridge A Level Physics", examCode: "9702" },
  { slug: "cambridge-a-level-psychology", name: "Psychology", level: "cambridge-a-level", colorKey: "other", dataFolder: "Psychology", dbName: "Cambridge A Level Psychology", examCode: "9990" },
  { slug: "cambridge-a-level-sociology", name: "Sociology", level: "cambridge-a-level", colorKey: "other", dataFolder: "Sociology", dbName: "Cambridge A Level Sociology", examCode: "9699" },
]
