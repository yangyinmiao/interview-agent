"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import FileUpload from "@/components/FileUpload";

export default function JDsPage() {
  const [jds, setJDs] = useState<any[]>([]);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());

  const loadJDs = () => {
    api.getJDs().then((data) => setJDs(data || [])).catch(() => {});
  };

  useEffect(() => {
    loadJDs();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这条 JD 吗？")) return;
    setDeleting((prev) => new Set(prev).add(id));
    try {
      await api.deleteJD(id);
      loadJDs();
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
          title="上传 JD"
          accept=".pdf,.docx,.txt,.md"
          onUpload={async (file) => {
            await api.uploadJD(file);
            loadJDs();
          }}
        />
      </div>

      <h2 className="text-lg font-semibold mb-4">已上传岗位描述</h2>

      {jds.length === 0 ? (
        <p className="text-gray-500 text-sm">暂无岗位描述</p>
      ) : (
        <div className="space-y-2">
          {jds.map((j: any) => (
            <div
              key={j.id}
              className="bg-white rounded-lg shadow p-4 flex justify-between items-center"
            >
              <div>
                <span className="font-medium">{j.filename}</span>
                <span className="ml-2 text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                  {j.parse_status}
                </span>
                <span className="ml-2 text-sm text-gray-500">
                  {new Date(j.created_at).toLocaleString("zh-CN")}
                </span>
              </div>
              <button
                onClick={() => handleDelete(j.id)}
                disabled={deleting.has(j.id)}
                className="text-red-500 hover:text-red-700 text-sm disabled:opacity-50"
              >
                {deleting.has(j.id) ? "删除中..." : "删除"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
