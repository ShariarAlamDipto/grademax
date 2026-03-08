'use client';

interface QuestionPreviewModalProps {
  question: {
    id: string;
    questionNumber: string;
    topics: string[];
    difficulty: string;
    qpPageUrl: string;
    msPageUrl: string | null;
    year: number;
    season: string;
    paper: string;
    hasDiagram: boolean;
  };
  isInBasket: boolean;
  onAdd: () => void;
  onRemove: () => void;
  onClose: () => void;
}

export default function QuestionPreviewModal({
  question,
  isInBasket,
  onAdd,
  onRemove,
  onClose,
}: QuestionPreviewModalProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-gray-900 border-b border-gray-700">
        <div>
          <h3 className="text-white font-bold text-lg">
            Q{question.questionNumber} — {question.year} {question.season} Paper {question.paper}
          </h3>
          <div className="flex items-center gap-2 mt-1">
            {question.topics.map((t) => (
              <span key={t} className="text-xs px-2 py-0.5 bg-blue-900/50 text-blue-300 rounded font-mono">
                {t}
              </span>
            ))}
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${
              question.difficulty === 'easy' ? 'bg-emerald-900/50 text-emerald-300' :
              question.difficulty === 'medium' ? 'bg-amber-900/50 text-amber-300' :
              question.difficulty === 'hard' ? 'bg-red-900/50 text-red-300' :
              'bg-gray-700 text-gray-300'
            }`}>
              {question.difficulty || 'Unknown'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {isInBasket ? (
            <button
              onClick={onRemove}
              className="bg-red-500/20 text-red-400 hover:bg-red-500/30 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Remove from Test
            </button>
          ) : (
            <button
              onClick={onAdd}
              className="bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              + Add to Test
            </button>
          )}
          <button
            onClick={onClose}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors"
          >
            Close
          </button>
        </div>
      </div>

      {/* PDF Preview(s) */}
      <div className="flex-1 flex gap-4 p-4 min-h-0">
        {/* Question Paper */}
        <div className="flex-1 flex flex-col min-w-0">
          <h4 className="text-sm font-semibold text-green-400 mb-2">Question Paper</h4>
          <iframe
            src={question.qpPageUrl}
            className="flex-1 w-full border border-gray-600 rounded-lg bg-white"
            title="Question Paper"
          />
        </div>

        {/* Mark Scheme */}
        {question.msPageUrl && (
          <div className="flex-1 flex flex-col min-w-0">
            <h4 className="text-sm font-semibold text-blue-400 mb-2">Mark Scheme</h4>
            <iframe
              src={question.msPageUrl}
              className="flex-1 w-full border border-gray-600 rounded-lg bg-white"
              title="Mark Scheme"
            />
          </div>
        )}
      </div>
    </div>
  );
}
