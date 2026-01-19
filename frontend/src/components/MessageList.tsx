import { useEffect, useRef } from 'react';
import { Message, Source } from '../types';
import ChatMessage from './ChatMessage';

interface MessageListProps {
  messages: Message[];
  deduplicateSources: (sources: Source[]) => Source[];
  onFollowUpClick: (question: string) => void;
  isLoading: boolean;
}

function MessageList({ messages, deduplicateSources, onFollowUpClick, isLoading }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Find the last assistant message index
  const lastAssistantIdx = messages.reduceRight(
    (acc, msg, idx) => (acc === -1 && msg.role === 'assistant' ? idx : acc),
    -1
  );

  return (
    <div className="space-y-6 pb-4">
      {messages.map((message, idx) => (
        <ChatMessage
          key={message.id}
          message={message}
          deduplicateSources={deduplicateSources}
          showFollowUps={idx === lastAssistantIdx && !isLoading}
          onFollowUpClick={onFollowUpClick}
        />
      ))}
      <div ref={endRef} />
    </div>
  );
}

export default MessageList;
