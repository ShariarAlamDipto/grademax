'use client';

import { useState } from 'react';

interface Topic {
  id: string;
  code: string;
  name: string;
}

interface TopicTreeProps {
  topics: Topic[];
  selectedTopics: string[];
  onToggle: (code: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
  loading?: boolean;
}

/**
 * Groups flat topics into chapters based on the leading digit(s) of the code.
 * e.g., "1a", "1b", "1c" → Chapter "1"
 *       "LOGS", "QUAD" → each is its own group (no numeric prefix)
 */
function groupTopicsIntoChapters(topics: Topic[]): { chapter: string; chapterName: string; items: Topic[] }[] {
  const groups: Record<string, Topic[]> = {};
  const chapterNames: Record<string, string> = {};

  for (const topic of topics) {
    // Try to extract leading number: "1a" → "1", "1b" → "1", "2a" → "2"
    const match = topic.code.match(/^(\d+)/);
    if (match) {
      const chapter = match[1];
      if (!groups[chapter]) {
        groups[chapter] = [];
        // Use the chapter number as name; we can derive a better name if the first topic has a pattern
        chapterNames[chapter] = `Chapter ${chapter}`;
      }
      groups[chapter].push(topic);
    } else {
      // Non-numeric code (e.g., "LOGS", "QUAD") — each is its own "chapter"
      groups[topic.code] = [topic];
      chapterNames[topic.code] = topic.name;
    }
  }

  return Object.entries(groups).map(([chapter, items]) => ({
    chapter,
    chapterName: chapterNames[chapter],
    items,
  }));
}

export default function TopicTree({ topics, selectedTopics, onToggle, onSelectAll, onClearAll, loading }: TopicTreeProps) {
  const [expandedChapters, setExpandedChapters] = useState<Record<string, boolean>>({});

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className="text-center p-6 bg-gray-800/30 rounded-xl">
        <p className="text-gray-400 text-sm">No topics available for this subject</p>
      </div>
    );
  }

  const chapters = groupTopicsIntoChapters(topics);
  const allSingleItems = chapters.every(c => c.items.length === 1);

  const toggleChapter = (chapter: string) => {
    setExpandedChapters(prev => ({ ...prev, [chapter]: !prev[chapter] }));
  };

  const isChapterFullySelected = (items: Topic[]) =>
    items.every(t => selectedTopics.includes(t.code));

  const isChapterPartiallySelected = (items: Topic[]) =>
    items.some(t => selectedTopics.includes(t.code)) && !isChapterFullySelected(items);

  const toggleChapterSelection = (items: Topic[]) => {
    if (isChapterFullySelected(items)) {
      // Deselect all in chapter
      items.forEach(t => {
        if (selectedTopics.includes(t.code)) onToggle(t.code);
      });
    } else {
      // Select all in chapter
      items.forEach(t => {
        if (!selectedTopics.includes(t.code)) onToggle(t.code);
      });
    }
  };

  return (
    <div>
      {/* Header with select/clear all */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">
          {selectedTopics.length} of {topics.length} topics selected
        </span>
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            Select All
          </button>
          <span className="text-gray-600">|</span>
          <button
            onClick={onClearAll}
            className="text-xs text-gray-400 hover:text-gray-300 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* If all chapters have just 1 item (like Pure Maths topics), render flat */}
      {allSingleItems ? (
        <div className="space-y-1">
          {topics.map((topic) => {
            const isSelected = selectedTopics.includes(topic.code);
            return (
              <button
                key={topic.id}
                onClick={() => onToggle(topic.code)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left ${
                  isSelected
                    ? 'bg-blue-900/50 border border-blue-500/50'
                    : 'bg-gray-800/30 border border-transparent hover:bg-gray-700/40'
                }`}
              >
                <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                  isSelected ? 'bg-blue-600 border-blue-400' : 'border-gray-500'
                }`}>
                  {isSelected && (
                    <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className="text-xs font-mono text-gray-400 w-12 flex-shrink-0">{topic.code}</span>
                <span className="text-sm text-white truncate">{topic.name}</span>
              </button>
            );
          })}
        </div>
      ) : (
        /* Collapsible chapter groups */
        <div className="space-y-1">
          {chapters.map(({ chapter, chapterName, items }) => {
            const isExpanded = expandedChapters[chapter] !== false; // default expanded
            const fullySelected = isChapterFullySelected(items);
            const partiallySelected = isChapterPartiallySelected(items);

            return (
              <div key={chapter} className="rounded-lg overflow-hidden">
                {/* Chapter header */}
                <div className="flex items-center bg-gray-800/60 hover:bg-gray-700/60 transition-colors">
                  <button
                    onClick={() => toggleChapterSelection(items)}
                    className="p-2.5 flex-shrink-0"
                  >
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                      fullySelected
                        ? 'bg-blue-600 border-blue-400'
                        : partiallySelected
                        ? 'bg-blue-600/50 border-blue-400/50'
                        : 'border-gray-500'
                    }`}>
                      {(fullySelected || partiallySelected) && (
                        <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="3"
                            d={partiallySelected ? "M5 12h14" : "M5 13l4 4L19 7"}
                          />
                        </svg>
                      )}
                    </div>
                  </button>
                  <button
                    onClick={() => toggleChapter(chapter)}
                    className="flex-1 flex items-center gap-2 py-2.5 pr-3 text-left"
                  >
                    <svg
                      className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="text-sm font-semibold text-white">{chapterName}</span>
                    <span className="text-xs text-gray-500 ml-auto">{items.length} topics</span>
                  </button>
                </div>

                {/* Chapter items */}
                {isExpanded && (
                  <div className="pl-4 space-y-0.5 py-1">
                    {items.map((topic) => {
                      const isSelected = selectedTopics.includes(topic.code);
                      return (
                        <button
                          key={topic.id}
                          onClick={() => onToggle(topic.code)}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all text-left ${
                            isSelected
                              ? 'bg-blue-900/40 border border-blue-500/30'
                              : 'border border-transparent hover:bg-gray-700/30'
                          }`}
                        >
                          <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-all ${
                            isSelected ? 'bg-blue-600 border-blue-400' : 'border-gray-600'
                          }`}>
                            {isSelected && (
                              <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </div>
                          <span className="text-xs font-mono text-gray-500 w-10 flex-shrink-0">{topic.code}</span>
                          <span className="text-sm text-gray-200">{topic.name}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
