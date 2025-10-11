/**
 * Core type definitions for the rebuilt architecture
 * Based on the full requirements spec
 */

// ============================================================================
// Geometry & Bounding Boxes
// ============================================================================

export interface BBox {
  page: number
  x: number
  y: number
  width: number
  height: number
}

export interface Point {
  x: number
  y: number
}

export interface Dimensions {
  width: number
  height: number
  dpi?: number
}

// ============================================================================
// Segmentation Types
// ============================================================================

export interface TextItem {
  text: string
  x: number
  y: number
  width: number
  height: number
  fontSize?: number
}

export interface QuestionFence {
  questionNumber: string
  totalMarks: number
  pageIndex: number
  yPosition: number
  textIndex: number
}

export interface SegmentedPart {
  code: string // "(a)", "(b)", "(a)(i)", etc.
  marks: number | null
  bboxList: BBox[] // Can span multiple pages
  text: string // For MS linking
  pageFrom: number
  pageTo: number
  hasStartMarker: boolean // Whether we found explicit (a), (b) marker
}

export interface SegmentedQuestion {
  questionNumber: string
  totalMarks: number
  contextText: string // Full stem + all parts (for tagging)
  headerBBox: BBox | null // Stem region (before first part)
  headerText: string // Stem text
  parts: SegmentedPart[]
  startPage: number
  endPage: number
}

export interface SegmentationResult {
  questions: SegmentedQuestion[]
  metadata: {
    totalQuestions: number
    totalParts: number
    fencesFound: number
    ocrUsed: boolean
    parsingErrors: string[]
  }
}

// ============================================================================
// Markscheme Types
// ============================================================================

export interface MSTableRow {
  questionNumber: string
  partCode: string // "(a)", "(a)(i)", etc.
  marks: number | null
  msPoints: string[] // Bullet points
  rawText: string
}

export interface MSLink {
  partId: string
  questionNumber: string
  partCode: string
  confidence: number // [0, 1]
  msPoints: string[]
  msSnippet: string // First 100 chars for QA
  matchDetails: {
    keyMatch: boolean // Composite key matched
    marksMatch: boolean // Marks equal
    cueOverlap: number // [0, 1] formula/keyword overlap
  }
}

export interface MSLinkResult {
  links: MSLink[]
  metadata: {
    totalParts: number
    linkedParts: number
    highConfidenceCount: number // ≥ 0.8
    averageConfidence: number
  }
}

// ============================================================================
// Tagging Types
// ============================================================================

export interface SpecStatement {
  id: string
  subjectId: string
  specRef: string // "P1.2.3"
  text: string
  topicId: string
  keywords: string[]
}

export interface MatchRule {
  id: string
  specStatementId: string
  ruleType: 'phrase' | 'regex' | 'formula'
  pattern: string
  weight: number
}

export interface TopicSignal {
  questionId: string
  topicId: string
  s1_sem: number // Semantic similarity
  s2_lex: number // Lexical match
  s3_kw: number // Keyword boost
  s4_struct: number // Structural features
  finalScore: number
  source: 'rule_phrase' | 'rule_formula' | 'ms_cue' | 'semantic'
}

export interface QuestionTag {
  questionId: string
  topicId: string
  confidence: number
  source: 'rule_phrase' | 'rule_formula' | 'ms_cue' | 'semantic'
  signals: TopicSignal
}

export interface TaggingResult {
  tags: QuestionTag[]
  metadata: {
    totalQuestions: number
    taggedQuestions: number
    averageTopicsPerQuestion: number
    cappedQuestions: number // Questions that hit the 4-topic cap
    ruleMatches: number
    msCueMatches: number
    semanticFallbacks: number
  }
}

// ============================================================================
// Metadata Detection Types
// ============================================================================

export interface DetectedMetadata {
  board: string // "Cambridge", "Edexcel", etc.
  level: string // "IGCSE", "IAL", etc.
  subjectCode: string // "4PH1", "9702", etc.
  subjectName: string // "Physics", "Chemistry", etc.
  paperType: 'QP' | 'MS'
  paperNumber: string // "1", "2", "42", etc.
  variant: string // "P", "R", etc.
  year: number
  season: string // "Jun", "Nov", "Mar"
  detectedFrom: 'page1' | 'ocr' | 'filename_fallback'
  confidence: number // [0, 1]
  canonicalKey: string // Storage path
  docHash: string // SHA256 for dedupe
  rawText?: string // For debugging
}

// ============================================================================
// PDF Building Types
// ============================================================================

export interface LayoutConfig {
  targetWidth: number // e.g., 470pt
  marginTop: number
  marginBottom: number
  marginLeft: number
  marginRight: number
  minFontSize: number // e.g., 9pt
  softScaleFloor: number // e.g., 0.9
  pageHeight: number // e.g., 842pt (A4)
}

export interface AnswerSpaceConfig {
  marks: number
  commandWords: string[]
  baseLines: number
  bonusLines: number
}

export interface WorksheetItem {
  questionId: string
  partCode: string | null // null = whole question
  marks: number
  bboxList: BBox[]
  answerSpaceLines: number
  specRefs: string[]
  msPoints?: string[]
  estimatedSeconds: number
  sourcePdfUrl: string
}

export interface PDFBuildResult {
  studentPdf: Buffer
  teacherPdf?: Buffer
  metadata: {
    totalPages: number
    totalMarks: number
    estimatedMinutes: number
    rasterFallbackCount: number
    vectorRegionCount: number
    layoutWarnings: string[]
  }
}

// ============================================================================
// Rulepack Types
// ============================================================================

export interface Rulepack {
  subject: string
  code: string
  specStatements: Array<{
    ref: string
    topicId: string
    text: string
    keywords: string[]
  }>
  phraseRules: Array<{
    pattern: string
    specRefs: string[]
    weight: number
  }>
  formulaRules: Array<{
    pattern: string // Regex
    specRefs: string[]
    weight: number
  }>
  commandWords: {
    tier1_recall: string[]
    tier2_calculate: string[]
    tier3_explain: string[]
  }
  aliases: Record<string, string> // "×" → "x", "ρ" → "rho"
}

// ============================================================================
// Worksheet Generation Types
// ============================================================================

export interface WorksheetGenerateRequest {
  subjectCode: string
  topicIds: string[]
  specRefs?: string[]
  difficulties?: ('easy' | 'medium' | 'hard')[]
  yearFrom?: number
  yearTo?: number
  yearsList?: number[]
  count: number
  mixPreset?: '60-30-10' | 'ascending' | 'random'
  wholeQuestion?: boolean // default: true
  onlyUnseen?: boolean
  teacherVersion?: boolean
  includeMarkscheme?: boolean
}

export interface WorksheetGenerateResponse {
  worksheetId: string
  questionCount: number
  partCount: number
  totalMarks: number
  estimatedMinutes: number
  yearRange: string
  topicCoverage: Record<string, number> // topicId → count
}

// ============================================================================
// QA & Verification Types
// ============================================================================

export interface MSVerificationItem {
  questionNumber: string
  partCode: string
  marks: number
  linked: boolean
  confidence: number
  hasPoints: boolean
  issues: string[]
}

export interface MSVerificationReport {
  worksheetId: string
  items: MSVerificationItem[]
  summary: {
    totalItems: number
    linkedItems: number
    highConfidence: number // ≥ 0.8
    averageConfidence: number
    issuesFound: number
  }
}

export interface QAAlert {
  type: 'low_confidence' | 'empty_topics' | 'ocr_used' | 'duplicate' | 'fence_violation'
  severity: 'warning' | 'error'
  questionId: string
  questionNumber: string
  message: string
  details: Record<string, unknown>
}

// ============================================================================
// Database Models (matching schema)
// ============================================================================

export interface DBQuestion {
  id: string
  paper_id: string
  question_number: string
  text: string // For backward compatibility
  context_text: string // Full context for tagging
  header_bbox: BBox | null
  header_visual_url: string | null
  total_marks: number | null
  marks: number | null // Legacy
  difficulty: 'easy' | 'medium' | 'hard'
  embedding: number[] | null
  quality_flags: string[]
  doc_hash: string | null
  created_at: string
  updated_at: string
}

export interface DBQuestionPart {
  id: string
  question_id: string
  code: string
  marks: number | null
  page_from: number
  page_to: number
  bbox_list: BBox[]
  visual_hash: string | null
  answer_space_lines: number
  ms_link_confidence: number
  ms_points: string[] | null
  ms_snippet: string | null
  features: Record<string, unknown> | null
  spec_refs: string[]
  diagram_urls: string[]
  diagram_dims: Dimensions | null
  created_at: string
  updated_at: string
}

export interface DBPaper {
  id: string
  subject_id: string
  paper_number: string
  year: number
  season: string
  pdf_url: string
  markscheme_pdf_url: string | null
  meta: DetectedMetadata | null
  doc_hash: string | null
  created_at: string
}

export interface DBIngestion {
  id: string
  board: string | null
  level: string | null
  subject_code: string | null
  year: number | null
  season: string | null
  paper_code: string | null
  qp_storage_url: string | null
  ms_storage_url: string | null
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error: string | null
  questions_count: number
  parts_count: number
  processed_at: string | null
  created_at: string
}

// ============================================================================
// Ingestion Pipeline Types
// ============================================================================

export interface IngestionJob {
  pdfPath: string
  msPdfPath: string | null
  subjectId: string
  options: {
    dryRun: boolean
    force: boolean // Ignore doc_hash and re-ingest
    skipMS: boolean
    skipTagging: boolean
  }
}

export interface IngestionResult {
  success: boolean
  paperId: string | null
  questionsCreated: number
  partsCreated: number
  topicsTagged: number
  msLinked: number
  errors: string[]
  warnings: string[]
  metadata: DetectedMetadata | null
  duration: number // ms
}

// ============================================================================
// Utility Types
// ============================================================================

export type Difficulty = 'easy' | 'medium' | 'hard'
export type PaperType = 'QP' | 'MS'
export type Season = 'Jan' | 'Mar' | 'Jun' | 'Nov'
export type IngestionStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type RuleType = 'phrase' | 'regex' | 'formula'
export type TopicSource = 'rule_phrase' | 'rule_formula' | 'ms_cue' | 'semantic'

// Helper type for partial updates
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>
