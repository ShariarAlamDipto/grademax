'use client';

import { QuestionItem } from './QuestionCard';

interface TestBasketProps {
  items: QuestionItem[];
  onRemove: (id: string) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onClearAll: () => void;
  onGenerate: () => void;
  generating: boolean;
  testTitle: string;
  onTitleChange: (title: string) => void;
}

export default function TestBasket({
  items,
  onRemove,
  onMoveUp,
  onMoveDown,
  onClearAll,
  onGenerate,
  generating,
  testTitle,
  onTitleChange,
}: TestBasketProps) {
  return (
    <div className="bg-gray-800/80 border border-gray-700 rounded-xl flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Your Test
          </h2>
          {items.length > 0 && (
            <button
              onClick={onClearAll}
              className="text-xs text-red-400 hover:text-red-300 transition-colors"
            >
              Clear All
            </button>
          )}
        </div>

        {/* Test Title Input */}
        <input
          type="text"
          value={testTitle}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Test title..."
          className="w-full px-3 py-2 text-sm bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Items list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5 min-h-0">
        {items.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-10 h-10 text-gray-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <p className="text-sm text-gray-500">No questions added yet</p>
            <p className="text-xs text-gray-600 mt-1">Browse and add questions from the center panel</p>
          </div>
        ) : (
          items.map((item, index) => (
            <div key={item.id} className="flex items-center gap-2 bg-gray-900/50 rounded-lg p-2 group">
              {/* Sequence number */}
              <span className="w-6 h-6 flex items-center justify-center bg-blue-600 text-white rounded-full text-xs font-bold flex-shrink-0">
                {index + 1}
              </span>

              {/* Question info */}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white">Q{item.questionNumber}</div>
                <div className="text-[10px] text-gray-400 truncate">
                  {item.year} {item.season} P{item.paper}
                </div>
              </div>

              {/* Reorder + Remove controls */}
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => onMoveUp(index)}
                  disabled={index === 0}
                  className="p-1 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  title="Move up"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7" />
                  </svg>
                </button>
                <button
                  onClick={() => onMoveDown(index)}
                  disabled={index === items.length - 1}
                  className="p-1 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  title="Move down"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <button
                  onClick={() => onRemove(item.id)}
                  className="p-1 text-red-400 hover:text-red-300 transition-colors"
                  title="Remove"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer stats + generate button */}
      <div className="p-4 border-t border-gray-700 space-y-3">
        {items.length > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Total Questions:</span>
            <span className="font-bold text-white">{items.length}</span>
          </div>
        )}

        <button
          onClick={onGenerate}
          disabled={items.length === 0 || generating}
          className="w-full bg-gradient-to-r from-emerald-500 to-green-600 text-white py-2.5 rounded-xl font-bold text-sm shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? 'Generating...' : 'Generate Test PDF'}
        </button>
      </div>
    </div>
  );
}
