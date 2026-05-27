"use client";

interface ReportViewProps {
  report: {
    overall_score?: number;
    scores?: Record<string, number>;
    strengths?: string[];
    weaknesses?: string[];
    suggestions?: string[];
    summary?: string;
  };
}

export default function ReportView({ report }: ReportViewProps) {
  if (!report || !report.scores) {
    return (
      <div className="text-center text-gray-500 py-8">
        报告生成中...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="text-center">
        <div className="text-3xl font-bold text-blue-600">
          {report.overall_score?.toFixed(1) ?? "-"}
        </div>
        <div className="text-sm text-gray-500">综合评分</div>
      </div>

      {report.scores && (
        <div>
          <h4 className="font-medium mb-2">各维度评分</h4>
          <div className="space-y-2">
            {Object.entries(report.scores).map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="text-sm w-32 text-gray-600">{key}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 rounded-full h-2"
                    style={{ width: `${(Number(value) / 10) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium w-8">{Number(value).toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.strengths && report.strengths.length > 0 && (
        <div>
          <h4 className="font-medium text-green-700 mb-2">亮点</h4>
          <ul className="list-disc list-inside text-sm space-y-1">
            {report.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {report.weaknesses && report.weaknesses.length > 0 && (
        <div>
          <h4 className="font-medium text-red-700 mb-2">不足</h4>
          <ul className="list-disc list-inside text-sm space-y-1">
            {report.weaknesses.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {report.suggestions && report.suggestions.length > 0 && (
        <div>
          <h4 className="font-medium text-blue-700 mb-2">改进建议</h4>
          <ul className="list-disc list-inside text-sm space-y-1">
            {report.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {report.summary && (
        <div>
          <h4 className="font-medium mb-2">综合评价</h4>
          <p className="text-sm text-gray-700">{report.summary}</p>
        </div>
      )}
    </div>
  );
}
