import React, { useState } from 'react';
import { Sparkles, BookOpen, ArrowRight, Copy, Check } from 'lucide-react';
import SpeakButton from './SpeakButton.jsx';

export default function ModelAnswerCard({ modelAnswer, upgrader }) {
  const [copied, setCopied] = useState(false);

  const answerText = typeof modelAnswer === 'string'
    ? modelAnswer
    : modelAnswer?.model_answer || modelAnswer?.text || upgrader?.model_answer || '';
  const collocations = modelAnswer?.collocations || upgrader?.collocations || [];

  if (!answerText && (!collocations || collocations.length === 0)) {
    return null;
  }

  const handleCopy = async () => {
    if (!answerText) return;
    try {
      await navigator.clipboard.writeText(answerText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <section aria-label="Câu trả lời mẫu Band 8.5" className="overflow-hidden rounded-3xl border border-violet-100 bg-gradient-to-br from-violet-50/50 via-white to-indigo-50/30 p-6 shadow-sm sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-violet-100/70 pb-4">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/20">
            <Sparkles size={20} />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold text-slate-900 sm:text-lg">Câu trả lời mẫu Band 8.5+</h2>
              <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-[11px] font-extrabold text-violet-800">
                Native Examiner
              </span>
            </div>
            <p className="text-xs text-slate-500">Mẫu phát triển ý tự nhiên, cấu trúc phức phong phú & từ vựng học thuật C1-C2</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {answerText && (
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-950 active:scale-95"
              title="Sao chép bài mẫu"
            >
              {copied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
              <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
            </button>
          )}
          {answerText && (
            <div className="flex items-center gap-1.5 rounded-xl bg-white px-2 py-1 border border-slate-200 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-500 pl-1">Phát âm:</span>
              <SpeakButton text={answerText} />
            </div>
          )}
        </div>
      </div>

      {answerText && (
        <div className="mt-5 rounded-2xl border border-violet-100 bg-white p-5 shadow-xs sm:p-6">
          <p className="font-serif text-sm italic leading-8 text-slate-800 sm:text-base">
            &ldquo;{answerText}&rdquo;
          </p>
        </div>
      )}

      {collocations.length > 0 && (
        <div className="mt-6 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-violet-900">
            <BookOpen size={15} />
            <span>Từ vựng & Cụm từ nâng Band gợi ý</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {collocations.map((item, idx) => {
              const phrase = item.upgrade || item.phrase;
              return (
                <div key={idx} className="rounded-2xl border border-violet-100/90 bg-white p-4 shadow-xs transition hover:border-violet-300 hover:shadow-sm">
                  <div className="flex items-center gap-2 text-xs">
                    {item.original && (
                      <>
                        <span className="max-w-[110px] truncate text-slate-400 line-through">{item.original}</span>
                        <ArrowRight size={13} className="shrink-0 text-violet-500" />
                      </>
                    )}
                    <span className="font-extrabold text-violet-900">{phrase}</span>
                  </div>
                  {item.meaning && (
                    <p className="mt-2 text-xs leading-relaxed text-slate-600">{item.meaning}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
