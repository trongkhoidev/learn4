import React from 'react';
import { ArrowRight, CheckCircle2, CircleDot, AlertCircle, Sparkles } from 'lucide-react';

export default function FeedbackFocusCard({ comment, review }) {
  if (review) {
    const labelConfigs = {
      strength: {
        text: 'Điểm làm tốt',
        badge: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        icon: CheckCircle2,
        iconColor: 'text-emerald-600',
      },
      limitation: {
        text: 'Cần cải thiện',
        badge: 'bg-amber-50 text-amber-800 border-amber-200',
        icon: CircleDot,
        iconColor: 'text-amber-600',
      },
      error: {
        text: 'Lỗi cần sửa',
        badge: 'bg-rose-50 text-rose-800 border-rose-200',
        icon: AlertCircle,
        iconColor: 'text-rose-600',
      },
      optional_improvement: {
        text: 'Cách nói tự nhiên hơn',
        badge: 'bg-indigo-50 text-indigo-800 border-indigo-200',
        icon: Sparkles,
        iconColor: 'text-indigo-600',
      },
    };

    return (
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-slate-600">
        {/* Band Reason */}
        {review.band_reason_vi && (
          <div className="rounded-2xl bg-slate-50/70 p-4 border border-slate-100">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Cơ sở đánh giá Band điểm
            </p>
            <p className="mt-1.5 font-medium text-slate-800">
              {review.band_reason_vi}
            </p>
          </div>
        )}

        {/* Observations */}
        {review.observations?.length > 0 && (
          <div className="space-y-3">
            {review.observations.map((obs, index) => {
              const config = labelConfigs[obs.kind] || labelConfigs.strength;
              const Icon = config.icon;

              return (
                <div key={index} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${config.badge}`}>
                      <Icon size={12} className={config.iconColor} /> {config.text}
                    </span>
                  </div>

                  {obs.quote && (
                    <div className="mt-2.5 flex flex-wrap items-center gap-2 rounded-xl bg-slate-50/80 p-2.5 text-xs">
                      <blockquote className="font-semibold text-slate-700 italic">
                        &ldquo;{obs.quote}&rdquo;
                      </blockquote>
                      {obs.suggestion && (
                        <>
                          <ArrowRight size={13} className="text-slate-400" aria-hidden="true" />
                          <span className="font-bold text-indigo-700">{obs.suggestion}</span>
                        </>
                      )}
                    </div>
                  )}

                  {obs.explanation_vi && (
                    <p className="mt-2 text-xs leading-5 text-slate-600">
                      {obs.explanation_vi}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Next Band Gap */}
        {review.next_band_gap_vi && (
          <div className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-4">
            <p className="text-xs font-bold text-indigo-950 flex items-center gap-1.5">
              <Sparkles size={14} className="text-indigo-600" /> Yêu cầu để tiến tới Band cao hơn
            </p>
            <p className="mt-1 text-xs leading-5 text-indigo-900/90">
              {review.next_band_gap_vi}
            </p>
          </div>
        )}
      </div>
    );
  }

  if (!comment) return null;
  const content = typeof comment === 'string' ? comment : [comment.pros, comment.cons, comment.action].filter(Boolean).join('\n');
  return <p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-600">{content}</p>;
}
