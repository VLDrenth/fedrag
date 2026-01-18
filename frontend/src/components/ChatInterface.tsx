import { useState, useCallback } from 'react';
import { queryFed } from '../api/client';
import { HistoryMessage, Message, Source } from '../types';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const exampleQueries = [
  { text: "What has Powell said about inflation?", category: "speeches" },
  { text: "Summarize the latest FOMC statement", category: "statements" },
  { text: "How has the Fed's stance on employment changed?", category: "analysis" },
  { text: "Key risks mentioned in recent communications", category: "research" },
];

function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (question: string) => {
    setError(null);

    const history: HistoryMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await queryFed(question, history);

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  const deduplicateSources = (sources: Source[]): Source[] => {
    const seen = new Set<string>();
    return sources.filter((source) => {
      if (seen.has(source.doc_id)) return false;
      seen.add(source.doc_id);
      return true;
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-lg">
              {/* Geometric hexagon icon */}
              <div className="w-16 h-16 mx-auto mb-6 relative">
                <svg viewBox="0 0 64 64" className="w-full h-full">
                  <polygon
                    points="32,4 58,18 58,46 32,60 6,46 6,18"
                    fill="none"
                    stroke="url(#gradient)"
                    strokeWidth="1.5"
                    className="opacity-60"
                  />
                  <polygon
                    points="32,14 48,23 48,41 32,50 16,41 16,23"
                    fill="url(#gradient)"
                    className="opacity-10"
                  />
                  <defs>
                    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#2563eb" />
                      <stop offset="100%" stopColor="#4f46e5" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              <h2 className="text-2xl font-semibold text-stone-100 mb-2 tracking-tight">
                Federal Reserve Research
              </h2>
              <p className="text-stone-400 mb-8 leading-relaxed text-sm">
                Query speeches, statements, and policy documents using natural language.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {exampleQueries.map((query) => (
                  <button
                    key={query.text}
                    onClick={() => handleSubmit(query.text)}
                    className="query-card group text-left p-4 bg-[#243347] hover:bg-transparent rounded-xl border border-white/10 hover:border-blue-500/30 transition-all duration-200"
                  >
                    <span className="font-mono text-[10px] uppercase tracking-wider text-stone-500 group-hover:text-white/70 mb-2 block transition-colors">
                      {query.category}
                    </span>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm text-stone-300 group-hover:text-white transition-colors">
                        {query.text}
                      </span>
                      <svg className="w-4 h-4 text-stone-500 group-hover:text-white/70 transition-colors flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} deduplicateSources={deduplicateSources} />
        )}
      </div>

      {error && (
        <div className="mx-6 mb-4 flex items-center gap-3 bg-red-950/50 border border-red-800/50 text-red-300 px-4 py-3 rounded-xl animate-fade-in">
          <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm">{error}</span>
        </div>
      )}

      <div className="px-6 pb-6 pt-2 border-t border-white/10 bg-[#1a2942]">
        <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
      </div>
    </div>
  );
}

export default ChatInterface;
