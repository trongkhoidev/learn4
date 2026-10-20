import { ArrowRight, CheckCircle2 } from 'lucide-react';

function Correction({ error }) {
  const optional = error.error_or_improvement === 'optional_improvement';
  return (
    <article className="rounded-xl border border-slate-200 p-4">
      <p className={`text-[10px] font-bold uppercase tracking-wider ${optional ? 'text-indigo-600' : 'text-rose-600'}`}>{optional ? 'Gợi ý diễn đạt' : 'Ngữ pháp · Cần sửa'}</p>
      <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        <span className={optional ? 'text-slate-600' : 'text-rose-700'}>{error.error || error.wrong}</span>
        <ArrowRight size={14} className="shrink-0 text-slate-400" aria-hidden="true" />
        <span className="font-semibold text-indigo-700">{error.correct}</span>
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{error.explain || error.explanation}</p>
    </article>
  );
}

export default function GrammarErrorList({ errors = [], status = 'scored' }) {
  return (
    <section aria-label="Đối chiếu ngữ pháp" className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-bold text-slate-950">Chỉnh câu & cách diễn đạt</h3>
        <span className="text-xs text-slate-400">{errors.length} mục có dẫn chứng</span>
      </div>
      {!errors.length ? (
        <div className="flex items-start gap-3 text-sm text-slate-600">
          <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-slate-400" />
          <div><h3 className="font-semibold text-slate-800">{status === 'scored' ? 'Không có lỗi được xác nhận' : 'Chưa đủ bằng chứng ngữ pháp'}</h3><p className="mt-1 text-xs leading-5 text-slate-500">Nhận xét dựa trên phần lời nói nhận diện được.</p></div>
        </div>
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-2">{errors.slice(0, 2).map((error, index) => <Correction key={index} error={error} />)}</div>
          {errors.length > 2 && <details className="mt-4"><summary className="cursor-pointer text-xs font-bold text-indigo-700">Xem {errors.length - 2} mục còn lại</summary><div className="mt-3 grid gap-3 md:grid-cols-2">{errors.slice(2).map((error, index) => <Correction key={index} error={error} />)}</div></details>}
        </>
      )}
    </section>
  );
}
