function Band({ label, score }) {
  return (
    <div className="rounded border bg-white p-3 text-center">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-bold">{score ?? "-"}</div>
    </div>
  );
}

const COLOR_CLASS = { green: "text-green-600", yellow: "text-amber-500", red: "text-red-500" };

export default function FeedbackPanel({ result }) {
  if (!result) return null;
  const colored = result.color_coded_transcript || [];
  const words =
    colored.length > 0
      ? colored
      : (result.transcript || "").split(/\s+/).filter(Boolean).map((word) => ({ word, color: null }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div className="col-span-2 rounded border bg-blue-50 p-3 text-center sm:col-span-1">
          <div className="text-xs text-slate-500">Overall</div>
          <div className="text-2xl font-bold text-blue-700">{result.overall}</div>
        </div>
        <Band label="Pronunciation" score={result.pronun?.score} />
        <Band label="Fluency" score={result.fluency?.score} />
        <Band label="Grammar" score={result.grammar?.score} />
        <Band label="Vocabulary" score={result.vocab?.score} />
      </div>

      {result.fluency?.features && (
        <div className="text-xs text-slate-500">
          {result.fluency.features.words_per_minute != null && (
            <span className="mr-3">Tốc độ: {result.fluency.features.words_per_minute} wpm</span>
          )}
          {result.fluency.features.pause_ratio != null && (
            <span>Tạm ngừng: {Math.round(result.fluency.features.pause_ratio * 100)}%</span>
          )}
        </div>
      )}

      {result.transcript && (
        <div>
          <div className="mb-1 text-xs font-semibold text-slate-500">Transcript</div>
          <p className="rounded bg-white p-3 text-sm leading-relaxed">
            {words.map((w, i) => (
              <span key={i} className={COLOR_CLASS[w.color] || ""}>
                {w.word}{" "}
              </span>
            ))}
          </p>
        </div>
      )}
    </div>
  );
}
