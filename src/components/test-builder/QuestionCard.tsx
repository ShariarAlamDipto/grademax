'use client';

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
      className={`bg-gray-800/80 border rounded-xl p-4 transition-all hover:shadow-lg ${
        isInBasket ? 'border-blue-500/50 bg-blue-900/20' : 'border-gray-700 hover:border-gray-500'
      }`}
    >
      {/* Top row: Question number + year + difficulty */}
      <div className="flex items-start justify-between mb-2.5">
        <div>
          <h4 className="text-base font-bold text-white">Q{question.questionNumber}</h4>
          <p className="text-xs text-gray-400">
            {question.year} {question.season} &middot; Paper {question.paper}
          </p>
        </div>
        <DifficultyBadge level={question.difficulty} />
      </div>

      {/* Topic chips */}
      <div className="flex flex-wrap gap-1 mb-2.5">
        {question.topics.map((t) => (
          <span
            key={t}
            className="text-[10px] px-1.5 py-0.5 bg-gray-700/80 text-gray-300 rounded font-mono"
          >
            {t}
          </span>
        ))}
        {question.hasDiagram && (
          <span className="text-[10px] px-1.5 py-0.5 bg-purple-900/50 text-purple-300 rounded border border-purple-500/30">
            Diagram
          </span>
        )}
      </div>

      {/* Text excerpt */}
      {question.textExcerpt && (
        <p className="text-xs text-gray-400 line-clamp-2 mb-3 leading-relaxed">
          {question.textExcerpt}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-700/50">
        <button
          onClick={() => onPreview(question)}
          className="text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors"
        >
          Preview
        </button>
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
  );
}
