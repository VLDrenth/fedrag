import { useState, useCallback } from 'react';
import { queryFed } from '../api/client';
import { Message, Source } from '../types';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (question: string) => {
    setError(null);

    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await queryFed(question);

      // Add assistant message with sources
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
  }, []);

  // Deduplicate sources by doc_id for display
  const deduplicateSources = (sources: Source[]): Source[] => {
    const seen = new Set<string>();
    return sources.filter((source) => {
      if (seen.has(source.doc_id)) return false;
      seen.add(source.doc_id);
      return true;
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">Ask a question about Federal Reserve communications</p>
              <p className="text-sm text-gray-400">
                Examples: "What has Powell said about inflation?" or "Summarize the latest FOMC statement"
              </p>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} deduplicateSources={deduplicateSources} />
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}

export default ChatInterface;
