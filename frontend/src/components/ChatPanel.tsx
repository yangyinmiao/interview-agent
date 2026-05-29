"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";

interface Message {
  id: string;
  role: string;
  content: string;
  metadata?: {
    reference_answer?: string;
  };
  created_at?: string;
}

interface ChatPanelProps {
  messages: Message[];
  loading?: boolean;
  interviewId: string;
}

function ChatBubble({ msg, interviewId }: { msg: Message; interviewId: string }) {
  const [expanded, setExpanded] = useState(false);
  const [loadedAnswer, setLoadedAnswer] = useState<string | null>(null);
  const [loadingAnswer, setLoadingAnswer] = useState(false);

  const role = msg.role;

  // System message: simple centered text
  if (role === "system") {
    return (
      <div className="chat-row chat-row-system">
        <div className="chat-bubble chat-bubble-system">
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        </div>
      </div>
    );
  }

  const isInterviewer = role === "interviewer";
  const avatarLabel = isInterviewer ? "官" : "我";
  const senderLabel = isInterviewer ? "面试官" : "候选人";

  const toggleReference = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }
    if (!loadedAnswer) {
      setLoadingAnswer(true);
      try {
        const result = await api.getReferenceAnswer(interviewId, msg.id);
        setLoadedAnswer(result.reference_answer);
      } catch {
        setLoadedAnswer("获取参考答案失败，请稍后重试。");
      } finally {
        setLoadingAnswer(false);
      }
    }
    setExpanded(true);
  };

  return (
    <div className={`chat-row ${isInterviewer ? "chat-row-interviewer" : "chat-row-candidate"}`}>
      {/* Avatar — left for interviewer, right for candidate */}
      {isInterviewer && (
        <div className="chat-avatar chat-avatar-interviewer">{avatarLabel}</div>
      )}

      <div className={`chat-bubble-wrap ${isInterviewer ? "chat-bubble-wrap-interviewer" : "chat-bubble-wrap-candidate"}`}>
        <div className={`chat-label ${isInterviewer ? "chat-label-interviewer" : "chat-label-candidate"}`}>
          {senderLabel}
        </div>
        <div className={`chat-bubble ${isInterviewer ? "chat-bubble-interviewer" : "chat-bubble-candidate"}`}>
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>

          {/* Reference answer toggle — only for interviewer messages */}
          {isInterviewer && (
            <div>
              <button onClick={toggleReference} className="chat-reference-btn">
                <span>{expanded ? "▾" : "▸"}</span>
                <span>参考答案</span>
                {loadingAnswer && (
                  <span className="inline-block w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin ml-1" />
                )}
              </button>
              {expanded && (
                <div className="chat-reference-panel">
                  {loadedAnswer ? (
                    <div className="prose prose-sm max-w-none text-blue-900">
                      <ReactMarkdown>{loadedAnswer}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="text-sm text-gray-400">加载中...</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {!isInterviewer && (
        <div className="chat-avatar chat-avatar-candidate">{avatarLabel}</div>
      )}
    </div>
  );
}

export default function ChatPanel({ messages, loading, interviewId }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto py-4 bg-[#F5F5F5]">
      {messages.length === 0 && !loading && (
        <div className="text-center text-gray-400 py-12">
          面试即将开始...
        </div>
      )}

      {messages.map((msg) => (
        <ChatBubble key={msg.id} msg={msg} interviewId={interviewId} />
      ))}

      {loading && (
        <div className="chat-row chat-row-interviewer">
          <div className="chat-avatar chat-avatar-interviewer">官</div>
          <div className="chat-bubble-wrap chat-bubble-wrap-interviewer">
            <div className="chat-label chat-label-interviewer">面试官</div>
            <div className="chat-bubble chat-bubble-interviewer animate-pulse">
              <span className="text-gray-400">正在思考...</span>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
