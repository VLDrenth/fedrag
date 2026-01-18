import { useState } from 'react';
import { Source } from '../types';

interface SourceCardProps {
  source: Source;
}

const docTypeLabels: Record<string, string> = {
  speech: 'Speech',
  statement: 'Statement',
  minutes: 'Minutes',
  testimony: 'Testimony',
};

const docTypeColors: Record<string, string> = {
  speech: 'bg-violet-900/50 text-violet-300 border-violet-700/50',
  statement: 'bg-blue-900/50 text-blue-300 border-blue-700/50',
  minutes: 'bg-emerald-900/50 text-emerald-300 border-emerald-700/50',
  testimony: 'bg-amber-900/50 text-amber-300 border-amber-700/50',
};

function SourceCard({ source }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const typeLabel = docTypeLabels[source.doc_type] || source.doc_type;
  const typeColor = docTypeColors[source.doc_type] || 'bg-stone-800/50 text-stone-300 border-stone-600/50';

  return (
    <div className="bg-[#243347] rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-all duration-200 hover:shadow-sm">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-stone-100 text-sm leading-snug">
              {source.title}
            </h4>
            <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
              <span className={`px-2 py-1 rounded-md border font-medium ${typeColor}`}>
                {typeLabel}
              </span>
              <span className="text-stone-400">{source.date}</span>
              {source.speaker && (
                <>
                  <span className="text-stone-600">•</span>
                  <span className="text-stone-400 font-medium">{source.speaker}</span>
                </>
              )}
            </div>
          </div>
          <span
            className={`text-stone-500 flex-shrink-0 mt-1 transition-transform duration-200 ${
              isExpanded ? 'rotate-180' : ''
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </span>
        </div>
      </button>

      <div
        className={`overflow-hidden transition-all duration-200 ease-out ${
          isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 pb-4 border-t border-white/10">
          <p className="text-sm text-stone-300 mt-3 leading-relaxed whitespace-pre-wrap">
            {source.text}
          </p>
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-4 text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
          >
            View original document
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>
    </div>
  );
}

export default SourceCard;
