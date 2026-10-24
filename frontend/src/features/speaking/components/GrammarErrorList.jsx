import React from 'react';
import { ArrowRight, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';

function CorrectionCard({ error }) {
  const isOptional = error.error_or_improvement === 'optional_improvement';
  const wrong = error.error || error.wrong;
  const correct = error.correct;
  const explain = error.explain || error.explanation;

  return (
    <article className="flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-4 shadow-xs transition hover:border-slate-300 sm:p-5">
      <div>
        <div className="flex items-center gap-2">
          {isOptional ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-[10px] font-extrabold uppercase text-indigo-700">
              <Sparkles size={11} /> Gợi ý tự nhiên hơn
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[10px] font-extrabold uppercase text-rose-700">
              <AlertCircle size={11} /> Ngữ pháp · Cần sửa
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm font-medium">
          <span className="rounded-lg bg-rose-50/80 px-2.5 py-1 text-rose-700 line-through">
            {wrong}
          </span>
          <ArrowRight size={14} className="shrink-0 text-slate-400" aria-hidden="true" />
          <span className="rounded-lg bg-emerald-50 px-2.5 py-1 font-bold text-emerald-800">
            {correct}
          </span>
        </div>
      </div>

      {explain && (
        <p className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-600">
          {explain}
        </p>
      )}
    </article>
  );
}

export default function GrammarErrorList({ errors = [] }) {
  return (
    <section aria-label="Sửa lỗi ngữ pháp & diễn đạt" className="rounded-3xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-extrabold text-slate-900 sm:text-lg">
            Sửa lỗi câu & Hoàn thiện diễn đạt
          </h3>
          <p className="text-xs text-slate-500">Đối chiếu trực tiếp từ transcript để cải thiện độ chuẩn xác và tự nhiên</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
          {errors.length} điểm cần lưu ý
        </span>
      </div>

      {!errors.length ? (
        <div className="flex items-center gap-3 rounded-2xl bg-emerald-50/50 p-4 text-sm text-emerald-950 border border-emerald-100">
          <CheckCircle2 size={20} className="shrink-0 text-emerald-600" />
          <div>
            <h4 className="font-bold">Không phát hiện lỗi ngữ pháp nghiêm trọng</h4>
            <p className="mt-0.5 text-xs text-emerald-800/80">Thí sinh kiểm soát cấu trúc câu tốt trong phạm vi bài nói ghi nhận được.</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            {errors.map((error, index) => (
              <CorrectionCard key={index} error={error} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
