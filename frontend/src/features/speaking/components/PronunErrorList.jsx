import React from 'react';
import { Ear, Play } from 'lucide-react';

export default function PronunErrorList({
  problems = [],
  phonemeEvidence = [],
  onReplayPhrase,
}) {
  const candidates = (phonemeEvidence || []).filter(
    (item) => item && item.word && Number.isFinite(item.start) && Number.isFinite(item.end),
  );

  if (!problems?.length && !candidates.length) {
    return null;
  }

  return (
    <section
      aria-label="Phát âm cần nghe lại"
      className="rounded-3xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7"
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-extrabold text-slate-900 sm:text-lg flex items-center gap-2">
            <Ear className="w-5 h-5 text-amber-500" />
            Từ vựng cần chú ý phát âm ({candidates.length || problems.length})
          </h3>
          <p className="text-xs text-slate-500">
            Các từ cần nhấn rõ trọng âm, phát âm đầy đủ âm đuôi (ending sounds) hoặc nối âm tự nhiên
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {candidates.map((item, index) => {
          return (
            <div
              key={item.id || index}
              className="flex flex-col justify-between rounded-2xl border border-amber-100 bg-amber-50/40 p-4 transition hover:border-amber-200"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-slate-900">{item.word}</span>
                    {item.expected_phone && (
                      <span className="rounded-md bg-white px-2 py-0.5 text-xs font-bold text-amber-800 border border-amber-200">
                        /{item.expected_phone}/
                      </span>
                    )}
                  </div>
                  {onReplayPhrase && (
                    <button
                      type="button"
                      onClick={() => onReplayPhrase(item.start, item.end)}
                      className="inline-flex items-center gap-1 rounded-xl bg-white px-2.5 py-1 text-xs font-bold text-amber-800 border border-amber-200 shadow-xs hover:bg-amber-100 active:scale-95"
                    >
                      <Play size={12} fill="currentColor" /> Nghe lại
                    </button>
                  )}
                </div>

                {item.practice_hint_vi && (
                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    {item.practice_hint_vi}
                  </p>
                )}
              </div>
            </div>
          );
        })}

        {problems.map((item, index) => (
          <div
            key={index}
            className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Ý định:</span>
              <span className="font-bold text-indigo-700">{item.intended}</span>
              <span className="text-xs text-slate-400">→ nghe thành:</span>
              <span className="font-semibold text-rose-600 line-through">{item.heard}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
