export default function WritingResult({ result }) {
  if (!result) return null;
  const criteria = [
    ["Task Response", result.task_response?.score],
    ["Coherence & Cohesion", result.coherence_cohesion?.score],
    ["Lexical Resource", result.lexical_resource?.score],
    ["Grammatical Accuracy", result.grammatical_accuracy?.score],
  ];
  return (
    <div className="space-y-3">
      <div className="rounded bg-blue-50 p-3 text-center text-2xl font-bold text-blue-700">
        Overall {result.overall}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {criteria.map(([label, score]) => (
          <div key={label} className="rounded border bg-white p-2">
            <div className="text-xs text-slate-500">{label}</div>
            <div className="text-lg font-bold">{score ?? "-"}</div>
          </div>
        ))}
      </div>
      {result.errors?.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-semibold text-slate-500">Lỗi ({result.errors.length})</div>
          {result.errors.map((e, i) => (
            <div key={i} className="rounded bg-white p-2 text-sm">
              <span className="text-red-600 line-through">{e.original}</span>{" "}
              <span>→</span> <span className="text-green-600">{e.corrected}</span>
              {e.explain && <div className="text-xs text-slate-500">{e.explain}</div>}
            </div>
          ))}
        </div>
      )}
      {result.improved_sample && (
        <div className="rounded bg-white p-3 text-sm">
          <div className="mb-1 text-xs font-semibold text-slate-500">Bài mẫu cải thiện</div>
          {result.improved_sample}
        </div>
      )}
    </div>
  );
}
