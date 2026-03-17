'use client';

import PdfThumbnail from './PdfThumbnail';

export interface QuestionItem {
  id: string;
  questionNumber: string;
  topics: string[];
  difficulty: string;
  qpPageUrl: string;
  msPageUrl: string | null;
  hasDiagram: boolean;
  textExcerpt: string;
  year: number;
  season: string;
  paper: string;
}

function DifficultyBadge({ level }: { level: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    easy: { bg: 'bg-emerald-900/60 border-emerald-500/50', text: 'text-emerald-300', label: 'Easy' },
    medium: { bg: 'bg-amber-900/60 border-amber-500/50', text: 'text-amber-300', label: 'Medium' },
    hard: { bg: 'bg-red-900/60 border-red-500/50', text: 'text-red-300', label: 'Hard' },
  };
  const c = config[level] || { bg: 'bg-gray-700 border-gray-500/50', text: 'text-gray-300', label: level || '—' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

interface QuestionCardProps {
  question: QuestionItem;
  isInBasket: boolean;
  onAdd: (q: QuestionItem) => void;
  onRemove: (id: string) => void;
  onPreview: (q: QuestionItem) => void;
}

export default function QuestionCard({ question, isInBasket, onAdd, onRemove, onPreview }: QuestionCardProps) {
  return (
    <div
      className={`bg-gray-800/80 border rounded-xl overflow-hidden transition-all hover:shadow-lg ${
        isInBasket ? 'border-blue-500/50 bg-blue-900/20' : 'border-gray-700 hover:border-gray-500'
      }`}
    >
      {/* Image preview of question page */}
      <div
        className="relative cursor-pointer group"
        onClick={() => onPreview(question)}
      >
        <div className="w-full overflow-hidden bg-gray-900" style={{ maxHeight: 200 }}>
          <PdfThumbnail url={question.qpPageUrl} width={400} className="w-full" />
        </div>
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
          <span className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 text-gray-900 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-lg">
            Preview Question
          </span>
        </div>
      </div>

      {/* Info bar */}
      <div className="p-3">
        {/* Top row: Question number + year + difficulty */}
        <div className="flex items-start justify-between mb-2">
          <div>
            <h4 className="text-sm font-bold text-white">Q{question.questionNumber}</h4>
            <p className="text-[11px] text-gray-400">
              {question.year} {question.season} &middot; P{question.paper}
            </p>
          </div>
          <DifficultyBadge level={question.difficulty} />
        </div>

        {/* Topic chips */}
        <div className="flex flex-wrap gap-1 mb-2.5">
          {question.topics.slice(0, 3).map((t) => (
            <span key={t} className="text-[10px] px-1.5 py-0.5 bg-gray-700/80 text-gray-300 rounded font-mono">
              {t}
            </span>
          ))}
          {question.topics.length > 3 && (
            <span className="text-[10px] px-1.5 py-0.5 bg-gray-700/80 text-gray-400 rounded">
              +{question.topics.length - 3}
            </span>
          )}
          {question.hasDiagram && (
            <span className="text-[10px] px-1.5 py-0.5 bg-purple-900/50 text-purple-300 rounded border border-purple-500/30">
              Diagram
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end">
          {isInBasket ? (
            <button
              onClick={() => onRemove(question.id)}
              className="text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 px-3 py-1.5 rounded-lg font-medium transition-colors"
            >
              Remove
            </button>
          ) : (
            <button
              onClick={() => onAdd(question)}
              className="text-xs bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 px-3 py-1.5 rounded-lg font-medium transition-colors"
            >
              + Add to Test
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
