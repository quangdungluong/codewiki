import RepoInfo from '@/types/repoInfo';
import getRepoUrl from '@/utils/getRepoUrl';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEffect, useRef, useState } from 'react';
import Markdown from './Markdown';
import {
  createChatWebSocket,
  closeWebSocket,
  ChatCompletionRequest,
} from '@/utils/websocketClient';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface AskProps {
  repoInfo: RepoInfo;
  language: string;
  onRef?: (ref: { clearConversation: () => void }) => void;
}

const Ask: React.FC<AskProps> = ({ repoInfo, language = 'en', onRef }) => {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { messages } = useLanguage();
  const [conversationHistory, setConversationHistory] = useState<Message[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const responseRef = useRef<HTMLDivElement>(null);
  const webSocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);
  useEffect(() => {
    if (onRef) {
      onRef({ clearConversation });
    }
  }, [onRef]);

  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [response]);

  useEffect(() => {
    return () => {
      closeWebSocket(webSocketRef.current);
    };
  }, []);

  const clearConversation = () => {
    setQuestion('');
    setResponse('');
    setConversationHistory([]);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;
    handleConfirmAsk();
  };

  const handleConfirmAsk = async () => {
    setIsLoading(true);
    setResponse('');

    try {
      const initialMessage: Message = {
        role: 'user',
        content: question,
      };

      const newHistory: Message[] = [initialMessage];
      setConversationHistory(newHistory);

      const requestBody: ChatCompletionRequest = {
        repo_url: getRepoUrl(repoInfo),
        type: repoInfo.type,
        language: language,
        messages: newHistory.map((msg) => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
        })),
      };

      const apiResponse = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!apiResponse.ok) {
        throw new Error('Failed to get response from the server');
      }

      const reader = apiResponse.body?.getReader();
      const decoder = new TextDecoder();

      let fullResponse = '';
      while (true) {
        const { done, value } = await reader?.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullResponse += chunk;
        setResponse(fullResponse);

        setIsLoading(false);
      }
    } catch (error) {
      console.error(error);
      setResponse(messages['ask.error'] as string);
      setIsLoading(false);
    }
  };

  const [buttonWidth, setButtonWidth] = useState(0);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Measure button width and update state
  useEffect(() => {
    if (buttonRef.current) {
      const width = buttonRef.current.offsetWidth;
      setButtonWidth(width);
    }
  }, [messages.ask?.askButton, isLoading]);

  return (
    <div>
      <div>
        {/* Question input */}
        <form onSubmit={handleSubmit}>
          <div className='relative'>
            <input
              ref={inputRef}
              type='text'
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                messages.ask?.placeholder ||
                'What would you like to know about this codebase?'
              }
              className='block w-full rounded-md border border-[var(--border-color)] bg-[var(--input-bg)] text-[var(--foreground)] px-5 py-3.5 text-base shadow-sm focus:border-[var(--accent-primary)] focus:ring-2 focus:ring-[var(--accent-primary)]/30 focus:outline-none transition-all'
              style={{ paddingRight: `${buttonWidth + 24}px` }}
              disabled={isLoading}
            />
            <button
              ref={buttonRef}
              type='submit'
              disabled={isLoading || !question.trim()}
              className={`absolute right-3 top-1/2 transform -translate-y-1/2 px-4 py-2 rounded-md font-medium text-sm ${
                isLoading || !question.trim()
                  ? 'bg-[var(--button-disabled-bg)] text-[var(--button-disabled-text)] cursor-not-allowed'
                  : 'bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-primary)]/90 shadow-sm'
              } transition-all duration-200 flex items-center gap-1.5`}
            >
              {isLoading ? (
                <div className='w-4 h-4 rounded-full border-2 border-t-transparent border-white animate-spin' />
              ) : (
                <>
                  <svg
                    className='w-4 h-4'
                    fill='none'
                    viewBox='0 0 24 24'
                    stroke='currentColor'
                  >
                    <path
                      strokeLinecap='round'
                      strokeLinejoin='round'
                      strokeWidth={2}
                      d='M13 5l7 7-7 7M5 5l7 7-7 7'
                    />
                  </svg>
                  <span>{messages.ask?.askButton || 'Ask'}</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Response area */}
        {response && (
          <div className='border-t border-gray-200 dark:border-gray-700 mt-4'>
            <div
              ref={responseRef}
              className='p-4 max-h-[500px] overflow-y-auto'
            >
              <Markdown content={response} />
            </div>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && !response && (
          <div className='p-4 border-t border-gray-200 dark:border-gray-700'>
            <div className='flex items-center space-x-2'>
              <div className='animate-pulse flex space-x-1'>
                <div className='h-2 w-2 bg-purple-600 rounded-full'></div>
                <div className='h-2 w-2 bg-purple-600 rounded-full'></div>
                <div className='h-2 w-2 bg-purple-600 rounded-full'></div>
              </div>
              <span className='text-xs text-gray-500 dark:text-gray-400'>
                Thinking...
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Ask;
