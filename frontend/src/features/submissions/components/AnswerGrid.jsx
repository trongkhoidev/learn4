import { useEffect, useState } from "react";

export default function AnswerGrid({ count, onChange }) {
  const [values, setValues] = useState(Array(count || 0).fill(""));

  useEffect(() => {
    setValues(Array(count || 0).fill(""));
  }, [count]);

  function set(i, v) {
    const next = [...values];
    next[i] = v;
    setValues(next);
    onChange && onChange(next);
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 p-2">
      {Array.from({ length: count || 0 }).map((_, i) => (
        <div key={i} className="flex items-center gap-2 bg-slate-50 p-2 rounded-lg border border-slate-200 shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
          <span className="flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-full bg-slate-200 text-slate-700 font-bold text-xs">
            {i + 1}
          </span>
          <input
            className="w-full bg-transparent border-none p-1 text-sm text-slate-700 font-medium focus:outline-none focus:ring-0 placeholder-slate-300 uppercase tracking-wider"
            value={values[i]}
            placeholder="..."
            onChange={(e) => set(i, e.target.value)}
          />
        </div>
      ))}
    </div>
  );
}
