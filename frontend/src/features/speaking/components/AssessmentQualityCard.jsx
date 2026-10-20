import { AudioLines, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function AssessmentQualityCard({ quality }) {
  if (!quality) return null;
  const strong = quality.level === 'high';
  const label = strong ? 'Evidence tốt' : quality.level === 'medium' ? 'Evidence một phần' : 'Cần thêm evidence';
  const agreement = quality.provider_agreement == null ? null : Math.round(quality.provider_agreement * 100);
  return (
    <section aria-label="Độ phủ bằng chứng đánh giá" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${strong ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
            {strong ? <CheckCircle2 size={19} /> : <ShieldAlert size={19} />}
          </span>
          <div>
            <h2 className="font-bold text-slate-950">Độ phủ bằng chứng</h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">Chỉ số kiểm soát chất lượng pipeline, không phải xác suất đúng hoặc band IELTS.</p>
          </div>
        </div>
        <span className={`rounded-full px-3 py-1.5 text-xs font-bold ${strong ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>{label} · {quality.coverage_score}/100</span>
      </div>
      <div className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
        <div className="rounded-xl bg-slate-50 px-3 py-2.5"><span className="text-slate-400">STT đối chiếu</span><strong className="mt-1 block text-slate-800">{quality.provider_count} engine</strong></div>
        <div className="rounded-xl bg-slate-50 px-3 py-2.5"><span className="text-slate-400">Đồng thuận transcript</span><strong className="mt-1 block text-slate-800">{agreement == null ? 'Chưa đo' : `${agreement}%`}</strong></div>
        <div className="rounded-xl bg-slate-50 px-3 py-2.5"><span className="text-slate-400">Phạm vi</span><strong className="mt-1 block text-slate-800">{quality.scope === 'four_criteria' ? 'Đủ 4 tiêu chí' : '3 tiêu chí ngôn ngữ'}</strong></div>
      </div>
      {!!quality.blockers_vi?.length && <details className="mt-4"><summary className="cursor-pointer text-xs font-bold text-indigo-700">Vì sao chưa đạt evidence tối đa?</summary><ul className="mt-2 space-y-1.5 text-xs leading-5 text-slate-600">{quality.blockers_vi.map(reason => <li key={reason} className="flex gap-2"><AudioLines size={13} className="mt-1 shrink-0 text-slate-400" />{reason}</li>)}</ul></details>}
    </section>
  );
}
