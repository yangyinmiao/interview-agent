"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

// ── Icons ────────────────────────────────────────────────────────────────────

function FileIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
      />
    </svg>
  );
}

function BriefcaseIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0"
      />
    </svg>
  );
}

function UploadIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
    </svg>
  );
}

function PlusIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function TrashIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round"
        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
      />
    </svg>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function stripExt(filename: string) {
  return filename.replace(/\.[^.]+$/, "");
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({
  title,
  action,
  children,
}: {
  title: string;
  action: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  );
}

// ── Item card ─────────────────────────────────────────────────────────────────

function ItemCard({
  icon,
  title,
  lines,
  onDelete,
  deleting,
}: {
  icon: React.ReactNode;
  title: string;
  lines: string[];
  onDelete: () => void;
  deleting: boolean;
}) {
  const [hover, setHover] = useState(false);

  return (
    <div
      className="relative border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all cursor-default"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div className="flex items-start gap-3">
        <div className="text-gray-400 mt-0.5 shrink-0">{icon}</div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{title}</p>
          {lines.map((l, i) => (
            <p key={i} className="text-xs text-gray-400 mt-0.5">{l}</p>
          ))}
        </div>
      </div>

      {/* Delete button — appears on hover */}
      {hover && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          disabled={deleting}
          title="删除"
          className="absolute top-2 right-2 p-1 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
        >
          {deleting
            ? <span className="text-xs">…</span>
            : <TrashIcon className="w-3.5 h-3.5" />
          }
        </button>
      )}
    </div>
  );
}

// ── Resumes Section ───────────────────────────────────────────────────────────

function ResumesSection() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = () => api.getResumes().then((d) => setResumes(d || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await api.uploadResume(file);
      load();
    } catch {
      alert("上传失败");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这条简历吗？")) return;
    setDeleting((p) => new Set(p).add(id));
    try { await api.deleteResume(id); load(); }
    catch { alert("删除失败"); }
    finally { setDeleting((p) => { const n = new Set(p); n.delete(id); return n; }); }
  };

  return (
    <Section
      title="简历管理"
      action={
        <>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }}
          />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <UploadIcon className="w-4 h-4" />
            {uploading ? "上传中…" : "上传简历"}
          </button>
        </>
      }
    >
      {resumes.length === 0 ? (
        <p className="text-sm text-gray-400">暂无简历，点击右上角上传</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {resumes.map((r) => (
            <ItemCard
              key={r.id}
              icon={<FileIcon className="w-4 h-4" />}
              title={r.filename}
              lines={[`上传于 ${formatDate(r.created_at)}`]}
              onDelete={() => handleDelete(r.id)}
              deleting={deleting.has(r.id)}
            />
          ))}
        </div>
      )}
    </Section>
  );
}

// ── JDs Section ───────────────────────────────────────────────────────────────

function JDsSection() {
  const [jds, setJDs] = useState<any[]>([]);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [showCreate, setShowCreate] = useState(false);
  const [activeTab, setActiveTab] = useState<"text" | "file">("text");
  const [submitting, setSubmitting] = useState(false);

  // Tab 1 — fill in text
  const [textTitle, setTextTitle] = useState("");
  const [textCompany, setTextCompany] = useState("");
  const [textDesc, setTextDesc] = useState("");

  // Tab 2 — upload file
  const [fileTitle, setFileTitle] = useState("");
  const [fileCompany, setFileCompany] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = () => api.getJDs().then((d) => setJDs(d || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const resetAll = () => {
    setTextTitle(""); setTextCompany(""); setTextDesc("");
    setFileTitle(""); setFileCompany(""); setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setShowCreate(false);
  };

  const handleTextSubmit = async () => {
    if (!textTitle.trim() || !textDesc.trim()) return;
    setSubmitting(true);
    try {
      await api.createJD({ title: textTitle.trim(), company: textCompany.trim() || undefined, description: textDesc.trim() });
      resetAll();
      load();
    } catch {
      alert("创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileSubmit = async () => {
    if (!selectedFile) return;
    setSubmitting(true);
    try {
      await api.uploadJD(selectedFile, fileTitle.trim() || undefined, fileCompany.trim() || undefined);
      resetAll();
      load();
    } catch {
      alert("上传失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这条岗位吗？")) return;
    setDeleting((p) => new Set(p).add(id));
    try { await api.deleteJD(id); load(); }
    catch { alert("删除失败"); }
    finally { setDeleting((p) => { const n = new Set(p); n.delete(id); return n; }); }
  };

  return (
    <Section
      title="岗位管理"
      action={
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          新建岗位
        </button>
      }
    >
      {/* Inline create panel */}
      {showCreate && (
        <div className="mb-4 p-4 border border-blue-200 bg-blue-50 rounded-xl space-y-3">
          <p className="text-sm font-medium text-blue-800">新建岗位</p>

          {/* Tabs */}
          <div className="flex gap-1 bg-white border border-gray-200 rounded-lg p-0.5 w-fit">
            <button
              onClick={() => setActiveTab("text")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${activeTab === "text" ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-700"}`}
            >
              填写信息
            </button>
            <button
              onClick={() => setActiveTab("file")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${activeTab === "file" ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-700"}`}
            >
              上传文件
            </button>
          </div>

          {activeTab === "text" ? (
            <div className="space-y-2">
              <input
                type="text"
                value={textTitle}
                onChange={(e) => setTextTitle(e.target.value)}
                placeholder="岗位名称（必填），例如：前端开发工程师"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <input
                type="text"
                value={textCompany}
                onChange={(e) => setTextCompany(e.target.value)}
                placeholder="公司名称（可选），例如：字节跳动"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <textarea
                value={textDesc}
                onChange={(e) => setTextDesc(e.target.value)}
                placeholder="请粘贴岗位 JD 内容…"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={handleTextSubmit}
                  disabled={submitting || !textTitle.trim() || !textDesc.trim()}
                  className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "创建中…" : "创建"}
                </button>
                <button onClick={resetAll} className="px-3 py-1.5 text-gray-500 text-sm hover:text-gray-700">
                  取消
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <input
                type="text"
                value={fileTitle}
                onChange={(e) => setFileTitle(e.target.value)}
                placeholder="岗位名称（可选，默认使用文件名）"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                value={fileCompany}
                onChange={(e) => setFileCompany(e.target.value)}
                placeholder="公司名称（可选）"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                className="w-full text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-white file:text-blue-700 hover:file:bg-blue-100"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={handleFileSubmit}
                  disabled={submitting || !selectedFile}
                  className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "上传中…" : "上传"}
                </button>
                <button onClick={resetAll} className="px-3 py-1.5 text-gray-500 text-sm hover:text-gray-700">
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {jds.length === 0 ? (
        <p className="text-sm text-gray-400">暂无岗位，点击右上角新建</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {jds.map((j) => (
            <ItemCard
              key={j.id}
              icon={<BriefcaseIcon className="w-4 h-4" />}
              title={j.title || stripExt(j.filename)}
              lines={[
                ...(j.company ? [j.company] : []),
                `创建于 ${formatDate(j.created_at)}`,
              ]}
              onDelete={() => handleDelete(j.id)}
              deleting={deleting.has(j.id)}
            />
          ))}
        </div>
      )}
    </Section>
  );
}

// ── Question Banks Section ────────────────────────────────────────────────────

function QBanksSection() {
  const [qbanks, setQBanks] = useState<any[]>([]);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [showCreate, setShowCreate] = useState(false);
  const [bankName, setBankName] = useState("");
  const [createFiles, setCreateFiles] = useState<FileList | null>(null);
  const [creating, setCreating] = useState(false);
  const [addingFiles, setAddingFiles] = useState<Set<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const addFileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const load = () => api.getQuestionBanks().then((d) => setQBanks(d || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!bankName.trim()) return;
    setCreating(true);
    try {
      const files = createFiles ? Array.from(createFiles) : undefined;
      await api.createQuestionBank(bankName.trim(), files);
      setBankName("");
      setCreateFiles(null);
      setShowCreate(false);
      load();
    } catch {
      alert("创建失败");
    } finally {
      setCreating(false);
    }
  };

  const handleAddFiles = async (bankId: string) => {
    const input = addFileRefs.current[bankId];
    if (!input?.files?.length) return;
    setAddingFiles((p) => new Set(p).add(bankId));
    try {
      await api.addFilesToBank(bankId, Array.from(input.files));
      input.value = "";
      load();
    } catch {
      alert("添加文件失败");
    } finally {
      setAddingFiles((p) => { const n = new Set(p); n.delete(bankId); return n; });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个题库吗？")) return;
    setDeleting((p) => new Set(p).add(id));
    try { await api.deleteQuestionBank(id); load(); }
    catch { alert("删除失败"); }
    finally { setDeleting((p) => { const n = new Set(p); n.delete(id); return n; }); }
  };

  return (
    <Section
      title="面试资料"
      action={
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          新建资料
        </button>
      }
    >
      {/* Inline create form */}
      {showCreate && (
        <div className="mb-4 p-4 border border-blue-200 bg-blue-50 rounded-xl space-y-3">
          <p className="text-sm font-medium text-blue-800">新建面试资料</p>
          <input
            type="text"
            value={bankName}
            onChange={(e) => setBankName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder="资料名称，例如：深信服常见面试题"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.txt,.md"
              onChange={(e) => setCreateFiles(e.target.files)}
              className="flex-1 text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-white file:text-blue-700 hover:file:bg-blue-100"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !bankName.trim()}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 shrink-0"
            >
              {creating ? "创建中…" : "创建"}
            </button>
            <button
              onClick={() => { setShowCreate(false); setBankName(""); }}
              className="px-3 py-1.5 text-gray-500 text-sm hover:text-gray-700"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {qbanks.length === 0 ? (
        <p className="text-sm text-gray-400">暂无面试资料，点击右上角新建</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {qbanks.map((q) => (
            <div
              key={q.id}
              className="group relative border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start gap-3">
                <div className="text-gray-400 mt-0.5 shrink-0">
                  <FileIcon className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-800 truncate">{q.name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {q.description ? `包含：${q.description}` : "点击编辑查看资料内容"}
                  </p>
                  {/* Add files inline */}
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100">
                    <input
                      ref={(el) => { addFileRefs.current[q.id] = el; }}
                      type="file"
                      multiple
                      accept=".pdf,.txt,.md"
                      className="flex-1 text-xs text-gray-400 file:mr-2 file:py-0.5 file:px-2 file:rounded file:border-0 file:text-xs file:bg-gray-100 file:text-gray-600 hover:file:bg-gray-200"
                    />
                    <button
                      onClick={() => handleAddFiles(q.id)}
                      disabled={addingFiles.has(q.id)}
                      className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 shrink-0 whitespace-nowrap"
                    >
                      {addingFiles.has(q.id) ? "添加中…" : "添加"}
                    </button>
                  </div>
                </div>
              </div>

              {/* Delete on hover */}
              <button
                onClick={() => handleDelete(q.id)}
                disabled={deleting.has(q.id)}
                title="删除"
                className="absolute top-2 right-2 p-1 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-40"
              >
                <TrashIcon className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MaterialsPage() {
  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">资料管理</h1>
        <p className="text-gray-500 text-sm mt-1">管理你的简历、岗位和面试资料，让面试更加个性化</p>
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
          <span>个性化配置</span>
          <span>·</span>
          <span>提升识别精度</span>
          <span>·</span>
          <span>更精准的回答</span>
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-6">
        <ResumesSection />
        <JDsSection />
        <QBanksSection />
      </div>
    </div>
  );
}
