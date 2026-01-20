import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
}

function ChatInput({ onSubmit, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed && !isLoading) {
      onSubmit(trimmed);
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div
        className={`bg-[#243347] rounded-xl border-2 transition-all duration-200 ${
          isFocused
            ? 'border-blue-500 shadow-lg shadow-blue-500/10'
            : 'border-white/10'
        }`}
      >
        <div className="flex items-end gap-3 p-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Ask about Federal Reserve policy, speeches, statements..."
            rows={1}
            className="flex-1 resize-none bg-transparent px-2 py-2 text-[15px] text-stone-100 placeholder-stone-500 focus:outline-none disabled:text-stone-500"
            disabled={isLoading}
            style={{ minHeight: '44px', maxHeight: '200px' }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 w-10 h-10 sm:w-11 sm:h-11 bg-gradient-to-br from-[#0a1628] to-[#1a2942] text-white rounded-lg flex items-center justify-center hover:from-[#1a2942] hover:to-[#2a3952] disabled:from-stone-300 disabled:to-stone-300 disabled:cursor-not-allowed transition-all duration-200 shadow-md disabled:shadow-none"
          >
            {isLoading ? (
              <svg className="animate-spin w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>
      </div>
      <div className="hidden sm:flex items-center justify-center gap-4 mt-3">
        <span className="text-xs text-stone-400">
          <kbd className="px-1.5 py-0.5 bg-[#0a1628] rounded text-stone-400 font-medium text-[10px]">↵</kbd> send
        </span>
        <span className="text-xs text-stone-400">
          <kbd className="px-1.5 py-0.5 bg-[#0a1628] rounded text-stone-400 font-medium text-[10px]">⇧↵</kbd> new line
        </span>
      </div>
    </form>
  );
}

export default ChatInput;
