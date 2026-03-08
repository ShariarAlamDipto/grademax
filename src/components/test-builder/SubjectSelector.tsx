'use client';

interface Subject {
  id: string;
  code: string;
  name: string;
  level?: string;
  board?: string;
}

interface SubjectSelectorProps {
  subjects: Subject[];
  selectedId: string;
  onSelect: (id: string) => void;
}

const SUBJECT_COLORS: Record<string, string> = {
  physics: 'border-orange-500 bg-orange-900/40',
  chemistry: 'border-violet-500 bg-violet-900/40',
  biology: 'border-emerald-500 bg-emerald-900/40',
  maths: 'border-sky-500 bg-sky-900/40',
  ict: 'border-red-500 bg-red-900/40',
  english: 'border-rose-500 bg-rose-900/40',
  default: 'border-indigo-500 bg-indigo-900/40',
};

function getSubjectColor(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, value] of Object.entries(SUBJECT_COLORS)) {
    if (key !== 'default' && lower.includes(key)) return value;
  }
  return SUBJECT_COLORS.default;
}

export default function SubjectSelector({ subjects, selectedId, onSelect }: SubjectSelectorProps) {
  // Group by level
  const igcse = subjects.filter(s => (s.level || '').toLowerCase() === 'igcse');
  const ial = subjects.filter(s => (s.level || '').toLowerCase() === 'ial');
  const other = subjects.filter(s => !['igcse', 'ial'].includes((s.level || '').toLowerCase()));

  const renderGroup = (label: string, items: Subject[]) => {
    if (items.length === 0) return null;
    return (
      <div className="mb-4">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">{label}</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {items.map((subject) => {
            const isSelected = selectedId === subject.id;
            const color = getSubjectColor(subject.name);
            return (
              <button
                key={subject.id}
                onClick={() => onSelect(subject.id)}
                className={`p-3 rounded-xl border-2 transition-all text-left ${
                  isSelected
                    ? `${color} shadow-lg scale-[1.02]`
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-500 hover:bg-gray-700/50'
                }`}
              >
                <div className="text-[10px] text-gray-400 font-mono">{subject.code}</div>
                <div className="text-sm font-semibold text-white truncate">{subject.name}</div>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div>
      {renderGroup('IGCSE', igcse)}
      {renderGroup('IAL / A-Level', ial)}
      {renderGroup('Other', other)}
    </div>
  );
}
