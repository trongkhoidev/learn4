import { CheckCircle2, ShieldAlert } from 'lucide-react';

export default function AssessmentQualityCard({ quality }) {
  if (!quality) return null;
  const strong = quality.level === 'high';
  const label = strong ? 'Evidence tốt' : quality.level === 'medium' ? 'Evidence một phần' : 'Cần thêm evidence';
  const agreement = quality.provider_agreement == null ? null : Math.round(quality.provider_agreement * 100);

  return (
    <section aria-label="Độ phủ bằng chứng đánh giá" className="rounded-2xl border border-slate-200/70 bg-slate-50/60 p-4 text-xs shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg ${strong ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'}`}>
            {strong ? <CheckCircle2 size={15} /> : <ShieldAlert size={15} />}
          </span>
          <div>
            <span className="font-bold text-slate-800">Độ phủ bằng chứng: </span>
            <span className="text-slate-500">Đối chiếu âm thanh từ các STT engines</span>
          </div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${strong ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>
          {label} · {quality.coverage_score}/100
        </span>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-lg border border-slate-100 bg-white p-2">
          <span className="block text-[10px] uppercase text-slate-400">STT đối chiếu</span>
          <strong className="text-slate-800">{quality.provider_count} engine</strong>
        </div>
        <div className="rounded-lg border border-slate-100 bg-white p-2">
          <span className="block text-[10px] uppercase text-slate-400">Đồng thuận transcript</span>
          <strong className="text-slate-800">{agreement == null ? 'Chưa đo' : `${agreement}%`}</strong>
        </div>
        <div className="rounded-lg border border-slate-100 bg-white p-2">
          <span className="block text-[10px] uppercase text-slate-400">Phạm vi</span>
          <strong className="text-slate-800">{quality.scope === 'four_criteria' ? 'Đủ 4 tiêu chí' : '3 tiêu chí ngôn ngữ'}</strong>
        </div>
      </div>
    </section>
  );
}
