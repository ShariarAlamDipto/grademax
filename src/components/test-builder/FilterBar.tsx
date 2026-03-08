'use client';

const CURRENT_YEAR = 2025;
const START_YEAR = 2011;
const YEARS = Array.from({ length: CURRENT_YEAR - START_YEAR + 1 }, (_, i) => CURRENT_YEAR - i);

interface FilterBarProps {
  difficulty: string;
  onDifficultyChange: (val: string) => void;
  yearStart: number;
  onYearStartChange: (val: number) => void;
  yearEnd: number;
  onYearEndChange: (val: number) => void;
}

export default function FilterBar({
  difficulty,
  onDifficultyChange,
  yearStart,
  onYearStartChange,
  yearEnd,
  onYearEndChange,
}: FilterBarProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Filters</h3>

      {/* Difficulty */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">Difficulty</label>
        <select
          value={difficulty}
          onChange={(e) => onDifficultyChange(e.target.value)}
          className="w-full p-2 text-sm border border-gray-600 bg-gray-800 text-white rounded-lg focus:border-blue-500 focus:outline-none"
        >
          <option value="">All</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      {/* Year Range */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">From</label>
          <select
            value={yearStart}
            onChange={(e) => onYearStartChange(parseInt(e.target.value))}
            className="w-full p-2 text-sm border border-gray-600 bg-gray-800 text-white rounded-lg focus:border-blue-500 focus:outline-none"
          >
            {YEARS.map((year) => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">To</label>
          <select
            value={yearEnd}
            onChange={(e) => onYearEndChange(parseInt(e.target.value))}
            className="w-full p-2 text-sm border border-gray-600 bg-gray-800 text-white rounded-lg focus:border-blue-500 focus:outline-none"
          >
            {YEARS.map((year) => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
