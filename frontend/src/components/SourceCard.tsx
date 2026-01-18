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
  speech: 'bg-purple-100 text-purple-800',
  statement: 'bg-blue-100 text-blue-800',
  minutes: 'bg-green-100 text-green-800',
  testimony: 'bg-orange-100 text-orange-800',
};

function SourceCard({ source }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const typeLabel = docTypeLabels[source.doc_type] || source.doc_type;
  const typeColor = docTypeColors[source.doc_type] || 'bg-gray-100 text-gray-800';

  return (
    <div className="bg-gray-50 rounded border border-gray-200 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left p-3 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-gray-900 text-sm truncate">
              {source.title}
            </h4>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
              <span className={`px-2 py-0.5 rounded-full ${typeColor}`}>
                {typeLabel}
              </span>
              <span>{source.date}</span>
              {source.speaker && <span>| {source.speaker}</span>}
            </div>
          </div>
          <span className="text-gray-400 flex-shrink-0">
            {isExpanded ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </span>
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-200">
          <p className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">
            {source.text}
          </p>
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-2 text-xs text-blue-600 hover:text-blue-800"
          >
            View original document
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      )}
    </div>
  );
}

export default SourceCard;
