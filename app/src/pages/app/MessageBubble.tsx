import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Compass } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from './mockData';
import ReasoningChain from './ReasoningChain';
import ToolCallCard from './ToolCallCard';

interface MessageBubbleProps {
  message: ChatMessage;
  isLatest?: boolean;
}

export default function MessageBubble({ message, isLatest = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isStreaming = !isUser && isLatest && message.isStreaming;
  const streamComplete = !isStreaming;

  const [displayedText, setDisplayedText] = useState(isStreaming ? '' : message.content);
  const streamingRef = useRef(false);
  const textRef = useRef(message.content);

  useEffect(() => {
    textRef.current = message.content;
  }, [message.content]);

  // Streaming typewriter effect for AI messages
  useEffect(() => {
    if (!isStreaming) {
      streamingRef.current = false;
      return;
    }

    if (streamingRef.current) return;
    streamingRef.current = true;

    const interval = setInterval(() => {
      setDisplayedText((prev) => {
        const target = textRef.current;
        if (prev.length < target.length) {
          return target.slice(0, prev.length + 1);
        }
        clearInterval(interval);
        return prev;
      });
    }, 12);

    return () => clearInterval(interval);
  }, [isStreaming]);

  const showCursor = isStreaming && displayedText.length < message.content.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} gap-3`}
    >
      {/* Agent Avatar */}
      {!isUser && (
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          style={{ background: 'linear-gradient(90deg, #2EC4B6 0%, #219EBC 100%)' }}
        >
          <Compass className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
        {/* Message Bubble */}
        <div
          className={isUser
            ? 'bg-[#1A659E] text-white px-4 py-3 rounded-2xl rounded-tr-sm'
            : 'px-4 py-3 rounded-2xl rounded-tl-sm border'
          }
          style={isUser
            ? {}
            : { background: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.08)' }
          }
        >
          {isUser ? (
            <p
              className="text-[#EDF6F9]"
              style={{ fontFamily: "'Inter Variable', Inter, sans-serif", fontSize: '0.9375rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}
            >
              {message.content}
            </p>
          ) : isStreaming ? (
            <p
              className="text-[#EDF6F9]"
              style={{ fontFamily: "'Inter Variable', Inter, sans-serif", fontSize: '0.9375rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}
            >
              {displayedText}
              {showCursor && (
                <span className="inline-block w-[2px] h-4 ml-0.5 bg-[#219EBC] animate-pulse align-middle" />
              )}
            </p>
          ) : (
            <div
              className="text-[#EDF6F9] markdown-body"
              style={{ fontFamily: "'Inter Variable', Inter, sans-serif", fontSize: '0.9375rem', lineHeight: 1.6 }}
            >
              <ReactMarkdown
                components={{
                  h1: ({ children }) => <h1 className="text-base font-semibold text-white mt-3 mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-sm font-semibold text-white mt-3 mb-1.5">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-xs font-semibold text-white mt-2 mb-1">{children}</h3>,
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                  li: ({ children }) => <li className="text-[#EDF6F9]">{children}</li>,
                  strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
                  code: ({ children }) => <code className="px-1 py-0.5 rounded text-[11px]" style={{ background: 'rgba(0,0,0,0.25)', fontFamily: "'JetBrains Mono Variable', monospace" }}>{children}</code>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span
          className="mt-1 text-xs"
          style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}
        >
          {message.timestamp}
        </span>

        {/* Reasoning Chain */}
        {!isUser && message.reasoningChain && streamComplete && (
          <div className="mt-2 w-full">
            <ReasoningChain steps={message.reasoningChain} />
          </div>
        )}

        {/* Tool Calls */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && streamComplete && (
          <div className="mt-2 w-full space-y-2">
            {message.toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
