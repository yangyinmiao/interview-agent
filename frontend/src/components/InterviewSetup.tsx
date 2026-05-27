"use client";

interface InterviewSetupProps {
  onStart: () => void;
  loading?: boolean;
}

export default function InterviewSetup({ onStart, loading }: InterviewSetupProps) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h3 className="text-lg font-medium mb-2">准备就绪</h3>
        <p className="text-gray-500 mb-4">点击开始，面试官将提出第一个问题</p>
        <button
          onClick={onStart}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "准备中..." : "开始面试"}
        </button>
      </div>
    </div>
  );
}
