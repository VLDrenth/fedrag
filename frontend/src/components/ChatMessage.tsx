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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white border border-gray-200 shadow-sm'
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>

        {sources.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm font-medium text-gray-600 mb-2">
              Sources ({sources.length})
            </p>
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
