import { ArrowRight, CheckCircle2, CircleDot } from 'lucide-react';

export default function FeedbackFocusCard({ comment, review }) {
  if (review) {
    const labels = {
      strength: 'Làm tốt', limitation: 'Cần cải thiện',
      error: 'Lỗi cần sửa', optional_improvement: 'Cách nói tự nhiên hơn',
    };
    return (
      <div className="mt-4 space-y-4 text-sm leading-6 text-slate-600">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Vì sao có band này?</p>
          <p className="mt-1 text-slate-800">{review.band_reason_vi}</p>
        </div>
        <div className="divide-y divide-slate-100">
          {review.observations.map((observation, index) => (
            <div key={index} className="py-3 first:pt-0 last:pb-0">
              <p className={`flex items-center gap-2 text-xs font-bold ${observation.kind === 'strength' ? 'text-emerald-700' : 'text-indigo-700'}`}>
                {observation.kind === 'strength' ? <CheckCircle2 size={14} /> : <CircleDot size={14} />}{labels[observation.kind] || 'Nhận xét'}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-2 rounded-lg bg-slate-50 px-3 py-2">
                <blockquote className="font-medium text-slate-700">“{observation.quote}”</blockquote>
                {observation.suggestion && <><ArrowRight size={13} className="text-slate-400" aria-hidden="true" /><span className="font-semibold text-indigo-700">{observation.suggestion}</span></>}
              </div>
              <p className="mt-1.5 text-xs leading-5">{observation.explanation_vi}</p>
            </div>
          ))}
        </div>
        <div className="border-t border-slate-100 pt-3">
          <p className="text-xs font-bold text-slate-800">Để tiến tới band cao hơn</p>
          <p className="mt-1 text-xs leading-5">{review.next_band_gap_vi}</p>
        </div>
      </div>
    );
  }
  if (!comment) return null;
  const content = typeof comment === 'string' ? comment : [comment.pros, comment.cons, comment.action].filter(Boolean).join('\n');
  if (content.length <= 450) return <p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-600">{content}</p>;
  return (
    <div className="mt-3 text-sm leading-6 text-slate-600">
      <p>{content.slice(0, 300)}…</p>
      <details className="mt-2"><summary className="cursor-pointer text-xs font-bold text-indigo-700">Xem nhận xét đầy đủ</summary><p className="mt-2 whitespace-pre-line">{content}</p></details>
    </div>
  );
}
