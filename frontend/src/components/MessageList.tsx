import { useEffect, useRef } from 'react';
import { Message, Source } from '../types';
import ChatMessage from './ChatMessage';

interface MessageListProps {
  messages: Message[];
  deduplicateSources: (sources: Source[]) => Source[];
}

function MessageList({ messages, deduplicateSources }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="space-y-4 pb-4">
      {messages.map((message) => (
        <ChatMessage
          key={message.id}
          message={message}
          deduplicateSources={deduplicateSources}
        />
      ))}
      <div ref={endRef} />
    </div>
  );
}

export default MessageList;
