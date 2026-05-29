"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// ── Icons ─────────────────────────────────────────────────────────────────────

function PlayIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
    </svg>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const MODE_LABELS: Record<string, string> = {
  basic: "基础问答",
  deep: "深入提问",
  follow_up: "追问模式",
  stress: "压力面试",
};

const MODE_DESCRIPTIONS: Record<string, string> = {
  basic: "标准面试流程，适合常规职位",
  deep: "深入技术细节，考察深度理解",
  follow_up: "针对回答追问，考察逻辑一致性",
  stress: "高压情境，考察抗压能力",
};

function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" }) +
    " " + d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(start: string | null, end: string | null) {
  if (!start || !end) return null;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const mins = Math.round(ms / 60000);
  return mins < 1 ? "< 1 分钟" : `${mins} 分钟`;
}

function stripExt(name: string) {
  return name?.replace(/\.[^.]+$/, "") ?? "";
}

// ── Start Interview Card ──────────────────────────────────────────────────────

function StartInterviewCard() {
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
    Promise.all([
      api.getResumes().catch(() => []),
      api.getJDs().catch(() => []),
      api.getQuestionBanks().catch(() => []),
    ]).then(([r, j, q]) => {
      setResumes(r || []);
      setJDs(j || []);
      setQBanks(q || []);
    });
  }, []);

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
    } catch {
      alert("创建面试失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="mb-5">
        <h2 className="text-base font-semibold text-gray-900">开始新面试</h2>
        <p className="text-sm text-gray-500 mt-0.5">选择资料和模式，AI 面试官将根据你的配置提问</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        {/* Resume */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">简历</label>
          <select
            value={selectedResume}
            onChange={(e) => setSelectedResume(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">不选择（无简历模式）</option>
            {resumes.map((r) => (
              <option key={r.id} value={r.id}>{r.filename}</option>
            ))}
          </select>
        </div>

        {/* JD */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">岗位 JD</label>
          <select
            value={selectedJD}
            onChange={(e) => setSelectedJD(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">不选择（通用面试）</option>
            {jds.map((j) => (
              <option key={j.id} value={j.id}>{stripExt(j.filename)}</option>
            ))}
          </select>
        </div>

        {/* Question Bank */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">面试资料</label>
          <select
            value={selectedQBank}
            onChange={(e) => setSelectedQBank(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">不使用资料库</option>
            {qbanks.map((q) => (
              <option key={q.id} value={q.id}>{q.name}</option>
            ))}
          </select>
        </div>

        {/* Mode */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5">面试模式</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {Object.entries(MODE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
          {mode && (
            <p className="text-xs text-gray-400 mt-1">{MODE_DESCRIPTIONS[mode]}</p>
          )}
        </div>
      </div>

      <button
        onClick={startInterview}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-3 rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm font-semibold"
      >
        <PlayIcon />
        {loading ? "准备面试中…" : "开始面试"}
      </button>
    </div>
  );
}

// ── Interviews History ────────────────────────────────────────────────────────

type Interview = {
  id: string;
  mode: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  resume_id?: string | null;
  jd_id?: string | null;
};

function StatusBadge({ status }: { status: string }) {
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
        已完成
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block animate-pulse" />
      进行中
    </span>
  );
}

function InterviewsHistory() {
  const router = useRouter();
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.getInterviews()
      .then((d) => setInterviews(d || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const toggle = (id: string) => setSelectedIds((p) => {
    const n = new Set(p);
    n.has(id) ? n.delete(id) : n.add(id);
    return n;
  });

  const toggleAll = () =>
    setSelectedIds(
      selectedIds.size === interviews.length
        ? new Set()
        : new Set(interviews.map((i) => i.id))
    );

  const deleteOne = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("确定要删除这条面试记录吗？")) return;
    try {
      await api.deleteInterview(id);
      setSelectedIds((p) => { const n = new Set(p); n.delete(id); return n; });
      load();
    } catch { alert("删除失败"); }
  };

  const batchDelete = async () => {
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条记录吗？`)) return;
    setDeleting(true);
    try {
      await api.deleteInterviews(Array.from(selectedIds));
      setSelectedIds(new Set());
      load();
    } catch { alert("删除失败"); }
    finally { setDeleting(false); }
  };

  const completed = interviews.filter((i) => i.status === "completed");
  const active = interviews.filter((i) => i.status !== "completed");

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-base font-semibold text-gray-900">面试历史</h2>
          {!loading && interviews.length > 0 && (
            <p className="text-sm text-gray-400 mt-0.5">
              共 {interviews.length} 次面试 · 已完成 {completed.length} 次
            </p>
          )}
        </div>
        {selectedIds.size > 0 && (
          <button
            onClick={batchDelete}
            disabled={deleting}
            className="flex items-center gap-1.5 text-sm text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
          >
            <TrashIcon />
            {deleting ? "删除中…" : `删除 ${selectedIds.size} 条`}
          </button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : interviews.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">🎯</div>
          <p className="text-gray-500 text-sm">还没有面试记录</p>
          <p className="text-gray-400 text-xs mt-1">完成上方配置后点击「开始面试」</p>
        </div>
      ) : (
        <>
          {/* Select all */}
          <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-100">
            <input
              type="checkbox"
              checked={selectedIds.size === interviews.length}
              onChange={toggleAll}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-400">全选</span>
          </div>

          {/* In-progress section */}
          {active.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">进行中</p>
              <div className="space-y-2">
                {active.map((i) => (
                  <InterviewRow
                    key={i.id}
                    interview={i}
                    selected={selectedIds.has(i.id)}
                    onToggle={() => toggle(i.id)}
                    onDelete={(e) => deleteOne(i.id, e)}
                    onClick={() => router.push(`/interview/${i.id}`)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Completed section */}
          {completed.length > 0 && (
            <div>
              {active.length > 0 && (
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2 mt-4">已完成</p>
              )}
              <div className="space-y-2">
                {completed.map((i) => (
                  <InterviewRow
                    key={i.id}
                    interview={i}
                    selected={selectedIds.has(i.id)}
                    onToggle={() => toggle(i.id)}
                    onDelete={(e) => deleteOne(i.id, e)}
                    onClick={() => router.push(`/interview/${i.id}`)}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function InterviewRow({
  interview: i,
  selected,
  onToggle,
  onDelete,
  onClick,
}: {
  interview: Interview;
  selected: boolean;
  onToggle: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onClick: () => void;
}) {
  const duration = formatDuration(i.started_at, i.completed_at);

  return (
    <div
      onClick={onClick}
      className={`group flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all ${
        selected
          ? "border-blue-300 bg-blue-50"
          : "border-gray-100 hover:border-gray-300 hover:bg-gray-50"
      }`}
    >
      {/* Checkbox */}
      <input
        type="checkbox"
        checked={selected}
        onChange={onToggle}
        onClick={(e) => e.stopPropagation()}
        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
      />

      {/* Mode icon area */}
      <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0 text-blue-600">
        <ChartIcon />
      </div>

      {/* Main info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-800">
            {MODE_LABELS[i.mode] ?? i.mode}
          </span>
          <StatusBadge status={i.status} />
        </div>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          <span className="text-xs text-gray-400">{formatDate(i.started_at)}</span>
          {duration && (
            <span className="text-xs text-gray-400">· 用时 {duration}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {i.status === "completed" && (
          <span className="hidden group-hover:flex items-center gap-1 text-xs text-blue-600 px-2 py-1 rounded-lg hover:bg-blue-50 mr-1">
            查看报告 <ArrowRightIcon />
          </span>
        )}
        <button
          onClick={onDelete}
          title="删除"
          className="p-1.5 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
        >
          <TrashIcon />
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <StartInterviewCard />
      <InterviewsHistory />
    </div>
  );
}
