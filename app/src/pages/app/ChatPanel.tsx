import { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Globe, Plus, MessageSquare, Loader2 } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTravel } from '@/contexts/TravelContext';
import MessageBubble from './MessageBubble';
import { quickActionChips } from './mockData';

export default function ChatPanel() {
  const { messages, status, sendMessage, resetSession, isBackendHealthy, checkBackendHealth } = useTravel();
  const [inputText, setInputText] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const isProcessing = status === 'processing';

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages]);

  // Check backend health once on mount
  useEffect(() => {
    if (isBackendHealthy === null) {
      checkBackendHealth();
    }
  }, [isBackendHealthy, checkBackendHealth]);

  const handleSubmit = () => {
    if (!inputText.trim() || isProcessing) return;
    const text = inputText.trim();
    setInputText('');
    sendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChipClick = (chip: string) => {
    if (isProcessing) return;
    sendMessage(chip);
  };

  const chatHistory = [
    { id: 'h1', title: 'Kyoto 5-Day Temple Tour', timestamp: '10:15 AM' },
    { id: 'h2', title: 'Tokyo Cherry Blossom Planning', timestamp: 'Yesterday' },
    { id: 'h3', title: 'Bali Beach & Culture Trip', timestamp: 'Mar 20' },
    { id: 'h4', title: 'Paris Weekend Getaway', timestamp: 'Mar 15' },
  ];

  return (
    <div className="flex flex-col h-full" style={{ background: 'rgba(10, 36, 99, 0.95)', backdropFilter: 'blur(12px)' }}>
      {/* Header */}
      <div className="flex-shrink-0 h-14 flex items-center justify-between px-4 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full animate-pulse ${isBackendHealthy === false ? 'bg-[#EF476F]' : 'bg-[#06D6A0]'}`} />
            <span className="text-sm font-semibold text-white" style={{ fontFamily: "'Outfit Variable', Outfit, sans-serif" }}>
              Chat
            </span>
          </div>
          {isProcessing && (
            <span className="text-[10px] text-[#8ECAE6]" style={{ fontFamily: "'Inter Variable', Inter, sans-serif" }}>
              规划中…
            </span>
          )}
        </div>
        <button
          onClick={resetSession}
          className="w-8 h-8 rounded-full flex items-center justify-center transition-all hover:scale-105"
          style={{ background: '#1A659E' }}
          title="New chat"
        >
          <Plus className="w-4 h-4 text-white" />
        </button>
      </div>

      {/* Chat History List */}
      <div className="flex-shrink-0 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)', maxHeight: '180px' }}>
        <ScrollArea className="h-full">
          <div className="py-1">
            {chatHistory.map((item, i) => (
              <div
                key={item.id}
                className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors ${i === 0 ? 'border-l-[3px] bg-[rgba(33,158,188,0.08)]' : 'border-l-[3px] border-transparent hover:bg-white/[0.05]'}`}
                style={i === 0 ? { borderLeftColor: '#219EBC' } : {}}
              >
                <MessageSquare className="w-4 h-4 flex-shrink-0 text-[#8ECAE6]" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs truncate" style={{ color: '#EDF6F9', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                    {item.title}
                  </p>
                </div>
                <span className="flex-shrink-0 text-[10px]" style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'JetBrains Mono Variable', monospace" }}>
                  {item.timestamp}
                </span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Messages Area */}
      <div className="flex-1 min-h-0">
        <ScrollArea ref={scrollRef} className="h-full">
          <div className="p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12 px-6">
                <p className="text-sm mb-2" style={{ color: 'rgba(255,255,255,0.6)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                  告诉我你想去哪里旅行
                </p>
                <p className="text-xs" style={{ color: 'rgba(255,255,255,0.35)', fontFamily: "'Inter Variable', Inter, sans-serif" }}>
                  例如："我想去杭州玩3天，预算3000元，喜欢自然和美食"
                </p>
              </div>
            )}
            {messages.map((msg, idx) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isLatest={idx === messages.length - 1}
              />
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Quick Action Chips */}
      <div className="flex-shrink-0 px-4 py-2 border-t" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {quickActionChips.map((chip) => (
            <button
              key={chip}
              onClick={() => handleChipClick(chip)}
              disabled={isProcessing}
              className="flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs transition-all hover:bg-white/[0.1] disabled:opacity-40"
              style={{
                background: 'rgba(255,255,255,0.06)',
                color: '#8ECAE6',
                fontFamily: "'Inter Variable', Inter, sans-serif",
              }}
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 px-4 py-3 border-t" style={{ background: 'rgba(10, 36, 99, 0.98)', borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2">
          <button className="flex-shrink-0 w-8 h-8 flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] transition-colors">
            <Paperclip className="w-4 h-4" />
          </button>
          <button className="flex-shrink-0 w-8 h-8 flex items-center justify-center text-[#EDF6F9] hover:text-[#8ECAE6] transition-colors">
            <Globe className="w-4 h-4" />
          </button>
          <div className="flex-1 relative">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your trip..."
              disabled={isProcessing}
              className="w-full h-10 rounded-full px-4 text-sm outline-none transition-colors focus:border-[#219EBC] disabled:opacity-50"
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#FFFFFF',
                fontFamily: "'Inter Variable', Inter, sans-serif",
                fontSize: '0.875rem',
              }}
            />
            <button
              onClick={handleSubmit}
              disabled={!inputText.trim() || isProcessing}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full flex items-center justify-center transition-all hover:scale-110 disabled:opacity-30"
              style={{ background: inputText.trim() ? '#E29578' : 'rgba(255,255,255,0.1)' }}
            >
              {isProcessing ? (
                <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5 text-white" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
