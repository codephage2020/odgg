// AI Chat panel — conversational model editing
import { useEffect, useRef, useState, useCallback } from 'react';
import { useChatStore, type ChatMessage } from '../../store/chatStore';
import { useSessionStore } from '../../store/sessionStore';
import { ChatInput } from './ChatInput';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

// Step-specific rendering helpers
function renderSuggestionContent(msg: ChatMessage) {
  const data = msg.suggestion;
  if (!data) return <p>{msg.content}</p>;

  if (msg.stepNumber === 3 && data.processes) {
    const procs = data.processes as Array<{ name: string; description?: string; confidence?: number }>;
    return (
      <div className="chat-suggestion">
        <p className="chat-ai-text">{msg.content}</p>
        {procs.map((p, i) => (
          <div key={i} className="chat-card">
            <strong>{p.name}</strong>
            {p.confidence != null && <span className="chat-conf">{Math.round(p.confidence * 100)}%</span>}
            {p.description && <p className="chat-card-desc">{p.description}</p>}
          </div>
        ))}
      </div>
    );
  }

  if (msg.stepNumber === 4 && data.options) {
    const opts = data.options as Array<{ description: string; recommended?: boolean }>;
    return (
      <div className="chat-suggestion">
        <p className="chat-ai-text">{msg.content}</p>
        {opts.map((o, i) => (
          <div key={i} className={`chat-card ${o.recommended ? 'chat-card-rec' : ''}`}>
            {o.recommended && <span className="rec-badge">推荐</span>}
            <p>{o.description}</p>
          </div>
        ))}
      </div>
    );
  }

  if (msg.stepNumber === 5 && data.dimensions) {
    const dims = data.dimensions as Array<{ name: string; source_table?: string; is_degenerate?: boolean }>;
    return (
      <div className="chat-suggestion">
        <p className="chat-ai-text">{msg.content}</p>
        <div className="chat-tags">
          {dims.map((d) => (
            <span key={d.name} className={`chat-tag ${d.is_degenerate ? 'chat-tag-degen' : ''}`}>
              {d.name}
            </span>
          ))}
        </div>
      </div>
    );
  }

  if (msg.stepNumber === 6 && data.measures) {
    const ms = data.measures as Array<{ name: string; aggregation?: string }>;
    return (
      <div className="chat-suggestion">
        <p className="chat-ai-text">{msg.content}</p>
        <div className="chat-tags">
          {ms.map((m) => (
            <span key={m.name} className="chat-tag">
              {m.name} <small>{m.aggregation || 'SUM'}</small>
            </span>
          ))}
        </div>
      </div>
    );
  }

  if (msg.stepNumber === 7 && data.model) {
    const model = data.model as { fact_table?: { name: string }; dimensions?: { name: string }[] };
    return (
      <div className="chat-suggestion">
        <p className="chat-ai-text">{msg.content}</p>
        <div className="chat-card">
          <strong>{model.fact_table?.name}</strong>
          <p>{model.dimensions?.length || 0} 个维度表</p>
        </div>
      </div>
    );
  }

  // Fallback
  return <p className="chat-ai-text">{msg.content}</p>;
}

function MessageBubble({
  msg,
  onAccept,
  onReject,
}: {
  msg: ChatMessage;
  onAccept?: () => void;
  onReject?: () => void;
}) {
  return (
    <div className={`chat-msg chat-msg-${msg.role}`}>
      {msg.role === 'ai' && <div className="chat-avatar">AI</div>}
      <div className="chat-bubble">
        {msg.role === 'system' ? (
          <p className="chat-system-text">{msg.content}</p>
        ) : msg.role === 'ai' && msg.suggestion ? (
          <>
            {renderSuggestionContent(msg)}
            {msg.status === 'complete' && onAccept && (
              <div className="chat-actions">
                <button className="btn btn-sm btn-accept" onClick={onAccept} aria-label="接受 AI 建议">接受</button>
                <button className="btn btn-sm btn-reject" onClick={onReject} aria-label="拒绝 AI 建议">拒绝</button>
              </div>
            )}
          </>
        ) : (
          <p>{msg.content}</p>
        )}
        {msg.status === 'streaming' && <span className="chat-typing" aria-label="AI 正在思考" />}
      </div>
    </div>
  );
}

export function AIChatPanel() {
  const { messages, addMessage, updateMessage } = useChatStore();
  const { session, loading, confirmStep, rollbackToStep, getSuggestion } = useSessionStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevStepRef = useRef<number | null>(null);
  const [sending, setSending] = useState(false);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  // Auto-trigger AI suggestion when step 3-7 becomes active
  useEffect(() => {
    if (!session || loading) return;
    const activeStep = session.steps.find((s) => s.status === 'active');
    if (
      activeStep &&
      activeStep.step_number >= 3 &&
      activeStep.step_number <= 7 &&
      activeStep.step_number !== prevStepRef.current
    ) {
      prevStepRef.current = activeStep.step_number;
      const stepNames: Record<number, string> = {
        3: '选择业务过程',
        4: '定义粒度',
        5: '选择维度',
        6: '定义度量',
        7: '构建模型',
      };
      addMessage({
        role: 'system',
        content: `Step ${activeStep.step_number}: ${stepNames[activeStep.step_number]}`,
        stepNumber: activeStep.step_number,
        status: 'complete',
      });

      const msgId = addMessage({
        role: 'ai',
        content: '正在分析...',
        stepNumber: activeStep.step_number,
        status: 'streaming',
      });

      getSuggestion(activeStep.step_number)
        .then((data) => {
          const contentMap: Record<number, string> = {
            3: `发现 ${(data.processes as unknown[])?.length || 0} 个业务过程：`,
            4: `推荐 ${(data.options as unknown[])?.length || 0} 个粒度选项：`,
            5: `建议 ${(data.dimensions as unknown[])?.length || 0} 个维度：`,
            6: `建议 ${(data.measures as unknown[])?.length || 0} 个度量：`,
            7: '模型构建完成：',
          };
          updateMessage(msgId, {
            content: contentMap[activeStep.step_number] || 'AI 建议：',
            suggestion: data,
            status: 'complete',
          });
        })
        .catch((err) => {
          updateMessage(msgId, {
            content: `分析失败: ${(err as Error).message}`,
            status: 'error',
          });
        });
    }
  }, [session, loading, getSuggestion, addMessage, updateMessage]);

  const handleAccept = useCallback(
    async (msg: ChatMessage) => {
      if (!msg.stepNumber) return;
      await confirmStep(msg.stepNumber);
      addMessage({
        role: 'system',
        content: `已接受 Step ${msg.stepNumber} 建议`,
        status: 'complete',
      });
    },
    [confirmStep, addMessage]
  );

  const handleReject = useCallback(
    async (msg: ChatMessage) => {
      if (!msg.stepNumber) return;
      await rollbackToStep(msg.stepNumber);
      prevStepRef.current = null; // Allow re-trigger
      addMessage({
        role: 'system',
        content: `已拒绝 Step ${msg.stepNumber}，正在重新分析...`,
        status: 'complete',
      });
    },
    [rollbackToStep, addMessage]
  );

  const handleSend = useCallback(
    async (text: string) => {
      if (!session) return;
      addMessage({ role: 'user', content: text, status: 'complete' });
      setSending(true);

      const msgId = addMessage({
        role: 'ai',
        content: '思考中...',
        status: 'streaming',
      });

      try {
        const resp = await fetch(`${API_BASE}/modeling/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: session.session_id, message: text }),
        });
        if (!resp.ok) {
          const errText = await resp.text();
          throw new Error(errText);
        }
        const data = await resp.json();
        updateMessage(msgId, {
          content: data.reply || '完成',
          status: 'complete',
        });
      } catch (err) {
        updateMessage(msgId, {
          content: `错误: ${(err as Error).message}`,
          status: 'error',
        });
      } finally {
        setSending(false);
      }
    },
    [session, addMessage, updateMessage]
  );

  // Find the latest AI suggestion message that hasn't been accepted yet
  const latestSuggestion = [...messages].reverse().find(
    (m) => m.role === 'ai' && m.suggestion && m.status === 'complete'
  );

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span>AI 助手</span>
      </div>
      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>连接数据源后，AI 将自动开始分析</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            onAccept={
              msg === latestSuggestion ? () => handleAccept(msg) : undefined
            }
            onReject={
              msg === latestSuggestion ? () => handleReject(msg) : undefined
            }
          />
        ))}
      </div>
      <ChatInput onSend={handleSend} disabled={sending || loading} />
    </div>
  );
}
