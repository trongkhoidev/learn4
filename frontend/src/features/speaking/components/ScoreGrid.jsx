import React from 'react';
import { Award, Volume2, BookOpen, CheckCircle2, Mic2, Sparkles, TrendingUp } from 'lucide-react';

const criteriaMeta = [
  {
    key: 'fluency',
    label: 'Fluency & Coherence',
    viLabel: 'Lưu loát & Mạch lạc',
    icon: Volume2,
    accent: 'bg-blue-500/10 text-blue-700 border-blue-200',
    indicator: 'bg-blue-600',
    border: 'hover:border-blue-300',
  },
  {
    key: 'vocabulary',
    label: 'Lexical Resource',
    viLabel: 'Vốn từ & Diễn đạt',
    icon: BookOpen,
    accent: 'bg-violet-500/10 text-violet-700 border-violet-200',
    indicator: 'bg-violet-600',
    border: 'hover:border-violet-300',
  },
  {
    key: 'grammar',
    label: 'Grammatical Range',
    viLabel: 'Ngữ pháp & Cấu trúc',
    icon: CheckCircle2,
    accent: 'bg-emerald-500/10 text-emerald-700 border-emerald-200',
    indicator: 'bg-emerald-600',
    border: 'hover:border-emerald-300',
  },
  {
    key: 'pronunciation',
    label: 'Pronunciation',
    viLabel: 'Phát âm & Ngữ điệu',
    icon: Mic2,
    accent: 'bg-amber-500/10 text-amber-700 border-amber-200',
    indicator: 'bg-amber-600',
    border: 'hover:border-amber-300',
  },
];

const getBandDescriptor = (band) => {
  if (band == null) return 'Đang cập nhật';
  const num = Number(band);
  if (num >= 8.5) return 'Expert User (Xuất sắc)';
  if (num >= 7.5) return 'Very Good User (Rất tốt)';
  if (num >= 7.0) return 'Good User (Thành thạo)';
  if (num >= 6.5) return 'Competent User+ (Khá tốt)';
  if (num >= 6.0) return 'Competent User (Đạt yêu cầu)';
  if (num >= 5.5) return 'Modest User+ (Cơ bản khá)';
  if (num >= 5.0) return 'Modest User (Cơ bản)';
  return 'Limited User (Cần cải thiện)';
};

export default function ScoreGrid({ scores = {} }) {
  const allCriteria = [
    scores.fluency?.band ?? scores.fluency?.score,
    scores.vocabulary?.band ?? scores.vocabulary?.score,
    scores.grammar?.band ?? scores.grammar?.score,
    scores.pronunciation?.band ?? scores.pronunciation?.score,
  ];

  const calcOverall = () => {
    if (scores.overall != null) return Number(scores.overall);
    const valid = allCriteria.filter(value => value != null && Number.isFinite(Number(value)) && Number(value) > 0);
    if (valid.length > 0) {
      const avg = valid.reduce((a, b) => a + Number(b), 0) / valid.length;
      return Math.floor(avg * 2 + 0.5) / 2;
    }
    return null;
  };

  const overall = calcOverall();
  const descriptor = getBandDescriptor(overall);
  const progressPercent = overall != null ? Math.min(Math.round((Number(overall) / 9.0) * 100), 100) : 0;

  return (
    <section aria-label="Bảng điểm IELTS Speaking" className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(300px,0.85fr)_minmax(0,2fr)]">
        {/* Hero Card: Overall Band */}
        <div className="relative isolate flex flex-col justify-between overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 p-6 text-white shadow-xl shadow-slate-950/20 sm:p-7 border border-indigo-950/50">
          <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-16 -z-10 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />
          <div aria-hidden="true" className="pointer-events-none absolute -left-12 -bottom-12 -z-10 h-40 w-40 rounded-full bg-blue-500/10 blur-2xl" />

          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-bold tracking-wider uppercase text-blue-200 backdrop-blur-md border border-white/10">
                <Award size={14} className="text-amber-400" /> IELTS Band Overall
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                <Sparkles size={12} /> Chuẩn IDP / BC
              </span>
            </div>

            <div className="mt-5 flex items-baseline gap-3">
              <span className="text-6xl font-black tracking-tight text-white sm:text-7xl">
                {overall == null ? '—' : Number(overall).toFixed(1)}
              </span>
              <span className="text-lg font-bold text-slate-400">/ 9.0</span>
            </div>

            <div className="mt-2 inline-flex items-center gap-2 rounded-xl bg-white/5 px-3 py-1.5 border border-white/10">
              <TrendingUp size={14} className="text-blue-300" />
              <span className="text-xs font-bold text-blue-100">{descriptor}</span>
            </div>
          </div>

          <div className="mt-6 border-t border-white/10 pt-4">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>Tiến độ đạt Band 9.0</span>
              <span className="font-bold text-white">{progressPercent}%</span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 via-indigo-400 to-emerald-400 transition-all duration-700 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* 4 Criteria Grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {criteriaMeta.map(({ key, label, viLabel, icon: Icon, accent, indicator, border }) => {
            const criterion = scores[key] || {};
            const value = criterion.band ?? criterion.score;

            return (
              <article
                key={key}
                className={`group relative flex flex-col justify-between overflow-hidden rounded-3xl border border-slate-200/90 bg-white p-4 shadow-sm transition-all duration-200 hover:shadow-md sm:p-5 ${border}`}
              >
                <div className={`absolute top-0 left-0 right-0 h-1.5 ${indicator}`} />

                <div>
                  <div className="flex items-center justify-between gap-1.5">
                    <span className={`grid h-8 w-8 place-items-center rounded-xl border ${accent}`}>
                      <Icon size={16} />
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                      IELTS
                    </span>
                  </div>

                  <h3 className="mt-3 text-xs font-extrabold text-slate-800 line-clamp-1 sm:text-sm">
                    {label}
                  </h3>
                  <p className="text-[11px] font-medium text-slate-500">
                    {viLabel}
                  </p>
                </div>

                <div className="mt-4 border-t border-slate-100 pt-3">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
                      {value == null ? '—' : Number(value).toFixed(1)}
                    </span>
                    <span className="text-xs font-bold text-slate-400">/ 9.0</span>
                  </div>
                  <p className="mt-1 text-[11px] font-bold text-emerald-700">
                    Band đạt được
                  </p>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
