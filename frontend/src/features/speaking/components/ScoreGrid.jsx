import React from 'react';
import { Award, CircleHelp } from 'lucide-react';

const criteria = [
  { key: 'fluency', label: 'Fluency & Coherence', accent: 'bg-blue-50 text-blue-700' },
  { key: 'vocabulary', label: 'Lexical Resource', accent: 'bg-violet-50 text-violet-700' },
  { key: 'grammar', label: 'Grammar', accent: 'bg-emerald-50 text-emerald-700' },
  { key: 'pronunciation', label: 'Pronunciation', accent: 'bg-amber-50 text-amber-700' },
];

const statusLabels = {
  partial: 'Một phần',
  insufficient_evidence: 'Chưa đủ evidence',
  needs_review: 'Cần nghe lại',
  failed: 'Chưa chấm được',
};

export default function ScoreGrid({ scores = {} }) {
  const overall = scores.overall;

  return (
    <section aria-label="Kết quả band chẩn đoán" className="grid gap-4 xl:grid-cols-[minmax(230px,.72fr)_minmax(0,1.8fr)]">
      <div className="relative isolate overflow-hidden rounded-[24px] bg-[#111b3d] p-5 text-white shadow-lg shadow-blue-950/10 sm:p-6">
        <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-12 -z-10 h-36 w-36 rounded-full border-[22px] border-white/[0.06]" />
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[.14em] text-blue-200">
          <Award size={16} aria-hidden="true" /> Band tổng thể
        </div>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-5xl font-extrabold tracking-tight sm:text-6xl">{overall == null ? '—' : Number(overall).toFixed(1)}</span>
          {overall != null && <span className="mb-2 text-sm font-semibold text-blue-200">/ 9</span>}
        </div>
        <div className="mt-4 flex items-start gap-2 border-t border-white/10 pt-4 text-xs leading-5 text-blue-100/75">
          <CircleHelp className="mt-0.5 shrink-0" size={14} aria-hidden="true" />
          <p>{overall == null ? 'Chỉ tính khi đủ evidence cho cả bốn tiêu chí.' : 'Đây là ước lượng chẩn đoán từ bài luyện, không phải điểm IELTS chính thức.'}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {criteria.map(({ key, label, accent }) => {
          const criterion = scores[key] || {};
          const value = criterion.band ?? criterion.score;
          const status = value != null ? 'Có căn cứ' : statusLabels[criterion.status] || 'Chưa đủ evidence';

          return (
            <article key={key} className="flex min-h-36 flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="max-w-32 text-xs font-bold leading-5 text-slate-600 sm:text-sm">{label}</h3>
                <span className={`hidden h-7 w-7 shrink-0 place-items-center rounded-lg text-[10px] font-extrabold sm:grid ${accent}`} aria-hidden="true">{label.slice(0, 1)}</span>
              </div>
              <div>
                <p className="text-3xl font-extrabold tracking-tight text-slate-950">{value == null ? '—' : Number(value).toFixed(1)}</p>
                <p className={`mt-2 text-[10px] font-semibold leading-4 ${value != null ? 'text-emerald-700' : 'text-slate-400'}`}>{status}</p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
