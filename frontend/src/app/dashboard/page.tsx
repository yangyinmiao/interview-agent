"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated, logout } from "@/lib/auth";
import FileUpload from "@/components/FileUpload";

export default function DashboardPage() {
  const router = useRouter();
  const [resumes, setResumes] = useState<any[]>([]);
  const [jds, setJDs] = useState<any[]>([]);
  const [qbanks, setQBanks] = useState<any[]>([]);
  const [selectedResume, setSelectedResume] = useState("");
  const [selectedJD, setSelectedJD] = useState("");
  const [selectedQBank, setSelectedQBank] = useState("");
  const [mode, setMode] = useState("basic");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    const [r, j, q] = await Promise.all([
      api.getResumes().catch(() => []),
      api.getJDs().catch(() => []),
      api.getQuestionBanks().catch(() => []),
    ]);
    setResumes(r || []);
    setJDs(j || []);
    setQBanks(q || []);
  };

  const startInterview = async () => {
    setLoading(true);
    try {
      const result = await api.createInterview({
        resume_id: selectedResume || undefined,
        jd_id: selectedJD || undefined,
        question_bank_id: selectedQBank || undefined,
        mode,
      });
      const started = await api.startInterview(result.id);
      router.push(`/interview/${result.id}`);
    } catch (err) {
      alert("Failed to start interview");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold">模拟面试 Agent</h1>
          <button
            onClick={logout}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            退出登录
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <FileUpload
            title="上传简历"
            accept=".pdf,.docx,.txt"
            onUpload={async (file) => {
              await api.uploadResume(file);
              await loadData();
            }}
          />
          <FileUpload
            title="上传 JD"
            accept=".pdf,.docx,.txt"
            onUpload={async (file) => {
              await api.uploadJD(file);
              await loadData();
            }}
          />
          <FileUpload
            title="上传题库"
            accept=".pdf,.txt"
            onUpload={async (file) => {
              await api.uploadQuestionBank(file);
              await loadData();
            }}
          />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">开始面试</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择简历
              </label>
              <select
                value={selectedResume}
                onChange={(e) => setSelectedResume(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">不选择（无简历模式）</option>
                {resumes.map((r: any) => (
                  <option key={r.id} value={r.id}>
                    {r.filename} ({r.parse_status})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择 JD
              </label>
              <select
                value={selectedJD}
                onChange={(e) => setSelectedJD(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">不选择（通用面试）</option>
                {jds.map((j: any) => (
                  <option key={j.id} value={j.id}>
                    {j.filename} ({j.parse_status})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                选择题库
              </label>
              <select
                value={selectedQBank}
                onChange={(e) => setSelectedQBank(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">不使用题库</option>
                {qbanks.map((q: any) => (
                  <option key={q.id} value={q.id}>
                    {q.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                面试模式
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="basic">基础问答</option>
                <option value="deep">深入提问</option>
                <option value="follow_up">追问模式</option>
                <option value="stress">压力面试</option>
              </select>
            </div>
          </div>

          <button
            onClick={startInterview}
            disabled={loading}
            className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors text-lg font-medium"
          >
            {loading ? "准备面试中..." : "开始面试"}
          </button>
        </div>

        {/* Interview History */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4">面试历史</h2>
          <InterviewsList />
        </div>
      </main>
    </div>
  );
}

function InterviewsList() {
  const [interviews, setInterviews] = useState<any[]>([]);

  useEffect(() => {
    api.getInterviews().then(setInterviews).catch(() => {});
  }, []);

  if (interviews.length === 0) {
    return <p className="text-gray-500 text-sm">暂无面试记录</p>;
  }

  return (
    <div className="space-y-2">
      {interviews.map((i: any) => (
        <div
          key={i.id}
          className="bg-white rounded-lg shadow p-4 flex justify-between items-center"
        >
          <div>
            <span className="font-medium">{i.mode}</span>
            <span
              className={`ml-2 text-xs px-2 py-0.5 rounded ${
                i.status === "completed"
                  ? "bg-green-100 text-green-700"
                  : "bg-blue-100 text-blue-700"
              }`}
            >
              {i.status === "completed" ? "已完成" : "进行中"}
            </span>
            <span className="ml-2 text-sm text-gray-500">
              {new Date(i.started_at).toLocaleString("zh-CN")}
            </span>
          </div>
          <a
            href={`/interview/${i.id}`}
            className="text-blue-600 hover:underline text-sm"
          >
            查看
          </a>
        </div>
      ))}
    </div>
  );
}
