import { useState, useCallback, useEffect } from 'react';
import { queryFed } from '../api/client';
import { HistoryMessage, Message, Source } from '../types';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const loadingMessages = [
  "Digging into the archives...",
  "Parsing Fed communications...",
  "Analyzing policy statements...",
  "Searching through speeches...",
  "Consulting the FOMC minutes...",
  "Reading between the lines...",
  "Decoding Fed speak...",
  "Following the money...",
];

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
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);

  // Cycle through loading messages
  useEffect(() => {
    if (!isLoading) {
      setLoadingMessageIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setLoadingMessageIndex((prev) => (prev + 1) % loadingMessages.length);
    }, 3500);
    return () => clearInterval(interval);
  }, [isLoading]);

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
        followUps: response.follow_ups,
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

  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="flex flex-col h-full">
      {messages.length > 0 && (
        <div className="px-4 md:px-6 py-3 border-b border-white/10 flex items-center justify-between">
          <span className="text-sm text-stone-400">
            {messages.length} message{messages.length !== 1 ? 's' : ''}
          </span>
          <button
            onClick={handleClear}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-stone-400 hover:text-stone-200 hover:bg-white/5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" className="origin-center rotate-45" />
            </svg>
            New conversation
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-lg">
              <h2 className="text-2xl font-semibold text-stone-100 mb-2 tracking-tight font-mono">
                Fed<span className="text-blue-400">/</span>RAG
              </h2>
              <p className="text-stone-400 mb-8 leading-relaxed text-sm">
                Query speeches, statements, and policy documents using natural language.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
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
          <>
            <MessageList
              messages={messages}
              deduplicateSources={deduplicateSources}
              onFollowUpClick={handleSubmit}
              isLoading={isLoading}
            />
            {isLoading && (
              <div className="flex items-start gap-3 mt-4">
                <div className="relative rounded-2xl px-5 py-4 border border-white/10 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-[#1a2942] via-[#243347] to-[#1a2942] animate-shimmer" />
                  <div className="relative flex items-center gap-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-stone-400 italic">
                      {loadingMessages[loadingMessageIndex]}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {error && (
        <div className="mx-4 md:mx-6 mb-4 flex items-center gap-3 bg-red-950/50 border border-red-800/50 text-red-300 px-4 py-3 rounded-xl animate-fade-in">
          <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm">{error}</span>
        </div>
      )}

      <div className="px-4 md:px-6 pb-4 md:pb-6 pt-2 border-t border-white/10 bg-[#1a2942]">
        <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
      </div>
    </div>
  );
}

export default ChatInterface;
