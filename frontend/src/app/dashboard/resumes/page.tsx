"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import FileUpload from "@/components/FileUpload";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<any[]>([]);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());

  const loadResumes = () => {
    api.getResumes().then((data) => setResumes(data || [])).catch(() => {});
  };

  useEffect(() => {
    loadResumes();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这条简历吗？")) return;
    setDeleting((prev) => new Set(prev).add(id));
    try {
      await api.deleteResume(id);
      loadResumes();
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
      <div className="mb-6">
        <FileUpload
          title="上传简历"
          accept=".pdf,.docx,.txt,.md"
          onUpload={async (file) => {
            await api.uploadResume(file);
            loadResumes();
          }}
        />
      </div>

      <h2 className="text-lg font-semibold mb-4">已上传简历</h2>

      {resumes.length === 0 ? (
        <p className="text-gray-500 text-sm">暂无简历</p>
      ) : (
        <div className="space-y-2">
          {resumes.map((r: any) => (
            <div
              key={r.id}
              className="bg-white rounded-lg shadow p-4 flex justify-between items-center"
            >
              <div>
                <span className="font-medium">{r.filename}</span>
                <span className="ml-2 text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                  {r.parse_status}
                </span>
                <span className="ml-2 text-sm text-gray-500">
                  {new Date(r.created_at).toLocaleString("zh-CN")}
                </span>
              </div>
              <button
                onClick={() => handleDelete(r.id)}
                disabled={deleting.has(r.id)}
                className="text-red-500 hover:text-red-700 text-sm disabled:opacity-50"
              >
                {deleting.has(r.id) ? "删除中..." : "删除"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
