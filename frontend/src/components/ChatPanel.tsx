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

export default function ChatPanel({ messages, loading, interviewId }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedAnswers, setExpandedAnswers] = useState<Set<string>>(new Set());
  const [loadedAnswers, setLoadedAnswers] = useState<Map<string, string>>(new Map());
  const [loadingAnswer, setLoadingAnswer] = useState<Set<string>>(new Set());

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleReferenceAnswer = async (msgId: string) => {
    if (expandedAnswers.has(msgId)) {
      // Collapse
      setExpandedAnswers((prev) => {
        const next = new Set(prev);
        next.delete(msgId);
        return next;
      });
      return;
    }

    // Expand - check if already loaded
    if (!loadedAnswers.has(msgId)) {
      setLoadingAnswer((prev) => new Set(prev).add(msgId));
      try {
        const result = await api.getReferenceAnswer(interviewId, msgId);
        setLoadedAnswers((prev) => {
          const next = new Map(prev);
          next.set(msgId, result.reference_answer);
          return next;
        });
      } catch (err) {
        setLoadedAnswers((prev) => {
          const next = new Map(prev);
          next.set(msgId, "获取参考答案失败，请稍后重试。");
          return next;
        });
      } finally {
        setLoadingAnswer((prev) => {
          const next = new Set(prev);
          next.delete(msgId);
          return next;
        });
      }
    }

    setExpandedAnswers((prev) => new Set(prev).add(msgId));
  };

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

          {msg.role === "interviewer" && (
            <div className="mt-2">
              <button
                onClick={() => toggleReferenceAnswer(msg.id)}
                className="text-xs text-gray-400 hover:text-blue-600 transition-colors flex items-center gap-1"
              >
                <span>{expandedAnswers.has(msg.id) ? "▾" : "▸"}</span>
                <span>参考答案</span>
                {loadingAnswer.has(msg.id) && (
                  <span className="inline-block w-3 h-3 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin ml-1" />
                )}
              </button>

              {expandedAnswers.has(msg.id) && (
                <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  {loadedAnswers.has(msg.id) ? (
                    <div className="prose prose-sm max-w-none text-blue-900">
                      <ReactMarkdown>{loadedAnswers.get(msg.id)!}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="text-sm text-gray-400">加载中...</div>
                  )}
                </div>
              )}
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
