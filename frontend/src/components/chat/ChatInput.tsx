// Chat input bar with send button
import { useState, useRef } from 'react';

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-bar">
      <textarea
        ref={inputRef}
        className="chat-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入修改指令，如: 添加一个时间维度..."
        disabled={disabled}
        rows={1}
      />
      <button
        className="btn btn-primary btn-sm chat-send"
        onClick={handleSend}
        disabled={disabled || !text.trim()}
      >
        发送
      </button>
    </div>
  );
}
