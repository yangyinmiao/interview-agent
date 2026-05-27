"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

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
      router.push(`/interview/${result.id}`);
    } catch (err) {
      alert("Failed to start interview");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
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

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4">面试历史</h2>
        <InterviewsList />
      </div>
    </div>
  );
}

function InterviewsList() {
  const [interviews, setInterviews] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const loadInterviews = () => {
    api.getInterviews().then(setInterviews).catch(() => {});
  };

  useEffect(() => {
    loadInterviews();
  }, []);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === interviews.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(interviews.map((i) => i.id)));
    }
  };

  const deleteOne = async (id: string) => {
    if (!confirm("确定要删除这条面试记录吗？")) return;
    try {
      await api.deleteInterview(id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      loadInterviews();
    } catch {
      alert("删除失败");
    }
  };

  const batchDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条面试记录吗？`)) return;

    setDeleting(true);
    try {
      await api.deleteInterviews(Array.from(selectedIds));
      setSelectedIds(new Set());
      loadInterviews();
    } catch {
      alert("删除失败");
    } finally {
      setDeleting(false);
    }
  };

  if (interviews.length === 0) {
    return <p className="text-gray-500 text-sm">暂无面试记录</p>;
  }

  const allSelected = selectedIds.size === interviews.length;

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <label className="flex items-center gap-1 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={toggleAll}
            className="rounded"
          />
          全选
        </label>
        {selectedIds.size > 0 && (
          <button
            onClick={batchDelete}
            disabled={deleting}
            className="text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
          >
            {deleting ? "删除中..." : `批量删除 (${selectedIds.size})`}
          </button>
        )}
      </div>

      <div className="space-y-2">
        {interviews.map((i: any) => (
          <div
            key={i.id}
            className={`bg-white rounded-lg shadow p-4 flex justify-between items-center ${
              selectedIds.has(i.id) ? "ring-2 ring-blue-400" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={selectedIds.has(i.id)}
                onChange={() => toggleSelect(i.id)}
                className="rounded"
              />
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
            </div>
            <div className="flex items-center gap-3">
              <a
                href={`/interview/${i.id}`}
                className="text-blue-600 hover:underline text-sm"
              >
                查看
              </a>
              <button
                onClick={() => deleteOne(i.id)}
                className="text-red-500 hover:text-red-700 text-sm"
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
