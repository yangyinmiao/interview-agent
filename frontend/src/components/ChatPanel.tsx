"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

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
  learningMode?: boolean;
}

export default function ChatPanel({ messages, loading, learningMode }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-2">
      {messages.length === 0 && !loading && (
        <div className="text-center text-gray-400 py-12">
          面试即将开始...
        </div>
      )}

      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`message-${
            msg.role === "interviewer"
              ? "interviewer"
              : msg.role === "candidate"
              ? "candidate"
              : "system"
          }`}
        >
          <div className="text-xs text-gray-400 mb-1">
            {msg.role === "interviewer" ? "面试官" : msg.role === "candidate" ? "候选人" : "系统"}
          </div>
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
          {learningMode && msg.role === "interviewer" && msg.metadata?.reference_answer && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="text-xs text-green-600 mb-1 font-medium">📝 参考答案</div>
              <div className="prose prose-sm max-w-none text-green-900">
                <ReactMarkdown>{msg.metadata.reference_answer}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      ))}

      {loading && (
        <div className="message-interviewer animate-pulse">
          <div className="text-xs text-gray-400 mb-1">面试官</div>
          <div className="text-gray-500">正在思考...</div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
