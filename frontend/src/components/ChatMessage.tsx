import Markdown from 'react-markdown';
import { Message, Source } from '../types';
import SourceCard from './SourceCard';

interface ChatMessageProps {
  message: Message;
  deduplicateSources: (sources: Source[]) => Source[];
}

function ChatMessage({ message, deduplicateSources }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const sources = message.sources ? deduplicateSources(message.sources) : [];

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-4 ${
          isUser
            ? 'bg-gradient-to-br from-[#0a1628] to-[#1a2942] text-white shadow-lg'
            : 'bg-[#1a2942] shadow-lg border border-white/10'
        }`}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</div>
        ) : (
          <div className="prose-fed">
            <Markdown>{message.content}</Markdown>
          </div>
        )}

        {sources.length > 0 && (
          <div className="mt-5 pt-4 border-t border-white/10">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-semibold text-stone-300">
                Sources ({sources.length})
              </span>
            </div>
            <div className="space-y-2">
              {sources.map((source) => (
                <SourceCard key={source.chunk_id} source={source} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatMessage;
