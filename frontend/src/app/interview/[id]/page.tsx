"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ChatPanel from "@/components/ChatPanel";
import ReportView from "@/components/ReportView";

export default function InterviewPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const router = useRouter();
  const [messages, setMessages] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("active");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [startError, setStartError] = useState(false);
  const [learningMode, setLearningMode] = useState(false);

  const loadMessages = async () => {
    try {
      const msgs = await api.getInterviewMessages(id);
      setMessages(msgs || []);
      if (msgs && msgs.length > 0) {
        setHasStarted(true);
      }
      try {
        const r = await api.getInterviewReport(id);
        if (r && r.scores) {
          setReport(r);
          setStatus("completed");
        }
      } catch {
        // Report not ready yet
      }
    } catch (err) {
      console.error("Failed to load messages", err);
    } finally {
      setInitializing(false);
    }
  };

  const loadReport = async () => {
    try {
      const r = await api.getInterviewReport(id);
      setReport(r);
    } catch {
      // Report might not be ready yet
    }
  };

  const startInterview = async () => {
    setLoading(true);
    setStartError(false);
    try {
      const result = await api.startInterview(id, learningMode);
      setHasStarted(true);
      if (result.status === "completed") {
        setStatus("completed");
        loadReport();
      }
      await loadMessages();
    } catch (err) {
      setStartError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Auto-start interview when page loads with no messages
  useEffect(() => {
    if (!initializing && !hasStarted && status === "active") {
      startInterview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initializing]);

  const submitAnswer = async () => {
    if (!answer.trim()) return;

    setLoading(true);
    const currentAnswer = answer;
    setAnswer("");

    try {
      const result = await api.respondToQuestion(id, currentAnswer, learningMode);
      await loadMessages();

      if (result.status === "completed") {
        setStatus("completed");
        loadReport();
      }
    } catch (err) {
      alert("Failed to submit answer");
    } finally {
      setLoading(false);
    }
  };

  const endInterview = async () => {
    setLoading(true);
    try {
      await api.endInterview(id);
      setStatus("completed");
      loadReport();
    } catch (err) {
      alert("Failed to end interview");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-sm border-b px-4 py-3 flex justify-between items-center">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-blue-600 hover:underline text-sm"
        >
          &larr; 返回控制台
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setLearningMode(!learningMode)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              learningMode
                ? "bg-green-100 text-green-700 border border-green-300"
                : "bg-gray-100 text-gray-500 border border-gray-200"
            }`}
          >
            {learningMode ? "📖 学习: 开" : "📖 学习: 关"}
          </button>
          <h1 className="font-semibold">模拟面试</h1>
        </div>
        {status === "active" && (
          <button
            onClick={endInterview}
            className="text-red-600 hover:underline text-sm"
          >
            结束面试
          </button>
        )}
        {status === "completed" && (
          <span className="text-green-600 text-sm font-medium">已完成</span>
        )}
      </header>

      {!hasStarted ? (
        <div className="flex-1 flex items-center justify-center">
          {(initializing || loading) && (
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-600">正在准备面试，请稍候...</p>
              <p className="text-gray-400 text-sm mt-2">AI 正在分析资料并生成面试问题</p>
            </div>
          )}
          {!initializing && !loading && startError && (
            <div className="text-center">
              <p className="text-red-600 mb-4">启动面试失败</p>
              <button
                onClick={startInterview}
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
              >
                重试
              </button>
            </div>
          )}
          {!initializing && !loading && !startError && (
            <button
              onClick={startInterview}
              className="bg-blue-600 text-white px-8 py-4 rounded-lg hover:bg-blue-700 text-lg"
            >
              开始面试
            </button>
          )}
        </div>
      ) : (
        <>
          <ChatPanel messages={messages} loading={loading} learningMode={learningMode} />

          {status === "completed" && report && (
            <div className="border-t bg-white">
              <ReportView report={report} />
            </div>
          )}

          {status === "active" && (
            <div className="border-t bg-white p-4">
              <div className="flex gap-3">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && e.shiftKey) {
                      e.preventDefault();
                      submitAnswer();
                    }
                  }}
                  placeholder="输入你的回答... (Shift+Enter 发送, Enter 换行)"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={3}
                  disabled={loading}
                />
                <button
                  onClick={submitAnswer}
                  disabled={loading || !answer.trim()}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors self-end"
                >
                  发送
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
