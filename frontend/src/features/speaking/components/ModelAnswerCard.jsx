import React from 'react';
import { Sparkles, BookOpen, ArrowRight } from 'lucide-react';
import SpeakButton from './SpeakButton.jsx';

export default function ModelAnswerCard({ modelAnswer, upgrader }) {
  const answerText = typeof modelAnswer === 'string'
    ? modelAnswer
    : modelAnswer?.model_answer || modelAnswer?.text || upgrader?.model_answer || '';
  const collocations = modelAnswer?.collocations || upgrader?.collocations || [];

  if (!answerText && (!collocations || collocations.length === 0)) {
    return null;
  }

  return (
    <section aria-label="Câu trả lời mẫu Band 8.5" className="overflow-hidden rounded-[24px] border border-violet-200 bg-gradient-to-br from-violet-50/70 via-white to-indigo-50/40 p-5 shadow-sm sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-violet-100 pb-4">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-violet-600 text-white shadow-sm">
            <Sparkles size={18} />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold text-slate-900">Câu trả lời mẫu Band 8.5+</h2>
              <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-[11px] font-extrabold text-violet-800">
                Native Examiner
              </span>
            </div>
            <p className="text-xs text-slate-500">Cấu trúc mở rộng, từ vựng C1-C2 và diễn đạt tự nhiên</p>
          </div>
        </div>
        {answerText && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">Nghe phát âm:</span>
            <SpeakButton text={answerText} />
          </div>
        )}
      </div>

      {answerText && (
        <div className="mt-5 rounded-2xl border border-violet-100 bg-white p-4 shadow-sm sm:p-5">
          <p className="font-serif text-sm italic leading-7 text-slate-800 sm:text-base">
            &ldquo;{answerText}&rdquo;
          </p>
        </div>
      )}

      {collocations.length > 0 && (
        <div className="mt-5 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-violet-900">
            <BookOpen size={14} />
            <span>Từ vựng & Diễn đạt nâng band gợi ý</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {collocations.map((item, idx) => {
              const phrase = item.upgrade || item.phrase;
              return (
                <div key={idx} className="rounded-xl border border-violet-100 bg-white p-3.5 shadow-xs transition hover:border-violet-300">
                  <div className="flex items-center gap-1.5 text-xs">
                    {item.original && (
                      <>
                        <span className="max-w-[110px] truncate text-slate-400 line-through">{item.original}</span>
                        <ArrowRight size={12} className="shrink-0 text-violet-500" />
                      </>
                    )}
                    <span className="font-bold text-violet-800">{phrase}</span>
                  </div>
                  {item.meaning && (
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-600">{item.meaning}</p>
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
