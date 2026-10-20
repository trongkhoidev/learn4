export default function ReasoningCards({ errors }) {
  if (!errors || errors.length === 0) return null;
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-500">Lỗi ngữ pháp ({errors.length})</div>
      {errors.map((e, i) => (
        <div key={i} className="rounded border bg-white p-2 text-sm">
          <span className="text-red-600 line-through">{e.error}</span>
          {" → "}
          <span className="font-semibold text-green-600">{e.correct}</span>
          {e.explain && <div className="text-xs text-slate-500">{e.explain}</div>}
        </div>
      ))}
    </div>
  );
}
