'use client';

import './tools-refresh.css';
import { toolSubjectDisplayCode } from '@/lib/igcseToolSubjects';

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
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
          {items.map((subject) => {
            const isSelected = selectedId === subject.id;
            return (
              <button
                key={subject.id}
                onClick={() => onSelect(subject.id)}
                aria-pressed={isSelected}
                className={`gm-subject ${isSelected ? 'gm-subject-on' : ''}`}
              >
                <div className="gm-subject-code">{toolSubjectDisplayCode(subject.code)}</div>
                <div className="gm-subject-name">{subject.name}</div>
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
