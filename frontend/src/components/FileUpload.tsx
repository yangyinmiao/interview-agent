"use client";

import { useState, useRef } from "react";

interface FileUploadProps {
  title: string;
  accept: string;
  onUpload: (file: File) => Promise<void>;
}

export default function FileUpload({ title, accept, onUpload }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessage("");
    try {
      await onUpload(file);
      setMessage("上传成功");
    } catch (err) {
      setMessage("上传失败");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 border-2 border-dashed border-gray-300 hover:border-blue-400 transition-colors">
      <h3 className="font-medium mb-2">{title}</h3>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleFile}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        disabled={uploading}
      />
      {uploading && <p className="text-blue-600 text-sm mt-1">上传中...</p>}
      {message && (
        <p className={`text-sm mt-1 ${message.includes("失败") ? "text-red-600" : "text-green-600"}`}>
          {message}
        </p>
      )}
    </div>
  );
}
