"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";

export default function QuestionBanksPage() {
  const [qbanks, setQBanks] = useState<any[]>([]);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [addingFiles, setAddingFiles] = useState<Set<string>>(new Set());
  const [bankName, setBankName] = useState("");
  const [createFiles, setCreateFiles] = useState<FileList | null>(null);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const createInputRef = useRef<HTMLInputElement>(null);

  const loadBanks = () => {
    api.getQuestionBanks().then((data) => setQBanks(data || [])).catch(() => {});
  };

  useEffect(() => {
    loadBanks();
  }, []);

  const handleCreate = async () => {
    if (!bankName.trim()) {
      setMessage("请输入题库名称");
      return;
    }

    setCreating(true);
    setMessage("");
    try {
      const files = createFiles ? Array.from(createFiles) : undefined;
      await api.createQuestionBank(bankName.trim(), files);
      setBankName("");
      setCreateFiles(null);
      if (createInputRef.current) createInputRef.current.value = "";
      setMessage("创建成功");
      loadBanks();
    } catch {
      setMessage("创建失败");
    } finally {
      setCreating(false);
    }
  };

  const handleAddFiles = async (bankId: string) => {
    const input = document.getElementById(`add-files-${bankId}`) as HTMLInputElement;
    const fileList = input?.files;
    if (!fileList || fileList.length === 0) return;

    setAddingFiles((prev) => new Set(prev).add(bankId));
    try {
      await api.addFilesToBank(bankId, Array.from(fileList));
      input.value = "";
      loadBanks();
    } catch {
      alert("添加文件失败");
    } finally {
      setAddingFiles((prev) => {
        const next = new Set(prev);
        next.delete(bankId);
        return next;
      });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个题库吗？")) return;
    setDeleting((prev) => new Set(prev).add(id));
    try {
      await api.deleteQuestionBank(id);
      loadBanks();
    } catch {
      alert("删除失败");
    } finally {
      setDeleting((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  return (
    <div>
      {/* Create new bank */}
      <div className="bg-white rounded-lg shadow p-4 border-2 border-dashed border-gray-300 hover:border-blue-400 transition-colors mb-6">
        <h3 className="font-medium mb-3">创建题库</h3>
        <div className="space-y-3">
          <input
            type="text"
            value={bankName}
            onChange={(e) => setBankName(e.target.value)}
            placeholder="输入题库名称，例如：AI应用开发题库"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <input
            ref={createInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.md"
            onChange={(e) => setCreateFiles(e.target.files)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {creating ? "创建中..." : "创建题库"}
          </button>
        </div>
        {message && (
          <p className={`text-sm mt-2 ${message.includes("失败") ? "text-red-600" : "text-green-600"}`}>
            {message}
          </p>
        )}
      </div>

      {/* Bank list */}
      <h2 className="text-lg font-semibold mb-4">已创建题库</h2>

      {qbanks.length === 0 ? (
        <p className="text-gray-500 text-sm">暂无题库，请先创建一个</p>
      ) : (
        <div className="space-y-3">
          {qbanks.map((q: any) => (
            <div
              key={q.id}
              className="bg-white rounded-lg shadow p-4"
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="font-medium text-base">{q.name}</span>
                  {q.description && (
                    <p className="text-sm text-gray-500 mt-0.5">
                      包含文件: {q.description}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(q.id)}
                  disabled={deleting.has(q.id)}
                  className="text-red-500 hover:text-red-700 text-sm disabled:opacity-50 ml-4 shrink-0"
                >
                  {deleting.has(q.id) ? "删除中..." : "删除"}
                </button>
              </div>

              {/* Add files row */}
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
                <input
                  id={`add-files-${q.id}`}
                  type="file"
                  multiple
                  accept=".pdf,.txt,.md"
                  className="flex-1 text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
                />
                <button
                  onClick={() => handleAddFiles(q.id)}
                  disabled={addingFiles.has(q.id)}
                  className="px-3 py-1.5 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50 shrink-0"
                >
                  {addingFiles.has(q.id) ? "添加中..." : "添加文件"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
