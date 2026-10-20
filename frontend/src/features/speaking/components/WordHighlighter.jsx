import { useState } from 'react';
import { ArrowRight, Check, Headphones, PencilLine, X } from 'lucide-react';

export default function WordHighlighter({ words = [], review, onWordClick, onReviewDecision }) {
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const suggestions = review?.suggestions || [];
  const byStart = new Map(suggestions.map(item => [item.word_ids[0], item]));
  const groupedIds = new Set(suggestions.flatMap(item => item.word_ids.slice(1)));
  const doubtful = word => word.uncertain || (word.color !== 'gray' && word.score != null && word.score < 60);
  const pendingCount = suggestions.filter(item => item.status === 'pending').length;
  const decidedIds = new Set(suggestions.filter(item => item.status !== 'pending').flatMap(item => item.word_ids));
  const unresolvedCount = words.filter(word => doubtful(word) && !decidedIds.has(word.id)).length;

  function select(group, suggestion) {
    const selected = words.filter(word => group.includes(word.id));
    setActive({ word_ids: group, quote: selected.map(word => word.word).join(' '), suggestion,
      start: selected[0]?.start, end: selected.at(-1)?.end });
    setDraft(suggestion?.confirmed_text || suggestion?.replacement || '');
    setError('');
    setSaved(false);
  }

  async function save(action) {
    if (!onReviewDecision || !active) return;
    setSaving(true);
    setError('');
    try {
      await onReviewDecision({ word_ids: active.word_ids, replacement: draft.trim(), action });
      setActive(null);
      setSaved(true);
    } catch (failure) {
      setError(failure.message || 'Chưa lưu được. Hãy thử lại.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-label="Transcript và đối chiếu" className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-5 sm:px-6">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.18em] text-indigo-600">Nghe · Hiểu · Đối chiếu</p>
          <h3 className="mt-1 text-lg font-bold tracking-tight text-slate-950">Transcript bài nói</h3>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">{pendingCount ? `${pendingCount} gợi ý cần xác nhận` : unresolvedCount ? `${unresolvedCount} từ cần nghe lại` : 'Đã đối chiếu xong'}</span>
      </header>

      <div className="px-4 py-5 sm:px-6">
        <div className="flex flex-wrap items-baseline gap-x-1 gap-y-2 text-base leading-8 text-slate-700" aria-label="Bản ghi gốc và gợi ý">
          {words.map((word, index) => {
            if (groupedIds.has(word.id)) return null;
            const suggestion = byStart.get(word.id);
            const accepted = suggestion?.status === 'accepted';
            const showArrow = suggestion && suggestion.status !== 'dismissed';
            const quote = suggestion?.quote || word.word;
            const isDoubtful = doubtful(word) && suggestion?.status !== 'dismissed';
            return (
              <button key={word.id || index} type="button" disabled={saving}
                onClick={() => { select(suggestion?.word_ids || [word.id], suggestion); onWordClick?.(word); }}
                aria-label={`Đối chiếu: ${quote}${showArrow ? ` → ${accepted ? suggestion.confirmed_text : suggestion.replacement}` : ''}`}
                className={`inline-flex max-w-full flex-wrap items-center gap-x-1.5 rounded-lg px-1.5 py-0.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${showArrow ? 'border border-indigo-100 bg-indigo-50/50' : isDoubtful ? 'border-b-2 border-amber-300 bg-amber-50/60' : 'hover:bg-slate-100'}`}
                title={showArrow ? accepted ? 'Bạn đã xác nhận cách ghi' : 'Gợi ý nhận diện, cần nghe lại để xác nhận' : isDoubtful ? 'Nhận diện chưa chắc. Chọn để nghe và đối chiếu.' : 'Chọn để nghe và đối chiếu'}>
                <span className={accepted ? 'text-slate-400 line-through decoration-slate-300' : showArrow || isDoubtful ? 'text-rose-700' : ''}>{quote}</span>
                {showArrow && <><ArrowRight size={13} className="text-slate-400" aria-hidden="true" /><span className="font-semibold text-indigo-700">{accepted ? suggestion.confirmed_text : suggestion.replacement}</span>{accepted && <Check size={13} className="text-emerald-600" aria-hidden="true" />}</>}
              </button>
            );
          })}
          {!words.length && <p className="text-sm text-slate-400">Chưa có transcript để đối chiếu.</p>}
        </div>

        {active && (
          <form onSubmit={event => { event.preventDefault(); save('accepted'); }} className="mt-5 rounded-2xl border border-indigo-100 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div><p className="text-xs font-bold text-slate-500">ĐOẠN ĐANG ĐỐI CHIẾU</p><p className="mt-1 font-semibold text-slate-900">“{active.quote}”</p></div>
              <button type="button" aria-label="Đóng đối chiếu" onClick={() => setActive(null)} disabled={saving} className="rounded-lg p-2 text-slate-400 hover:bg-white"><X size={16} /></button>
            </div>
            {active.suggestion && <p className="mt-2 text-sm leading-6 text-slate-600"><span className="font-semibold text-indigo-700">{active.suggestion.source === 'provided_term' ? 'Theo tên bạn cung cấp. ' : active.suggestion.source === 'alternate_decode' ? 'Theo lần nhận diện khác. ' : 'Gợi ý ngữ cảnh. '}</span>{active.suggestion.reason_vi}</p>}
            <button type="button" onClick={() => onWordClick?.(active)} disabled={!Number.isFinite(active.start) || !Number.isFinite(active.end)} className="mt-3 inline-flex min-h-9 items-center gap-2 text-xs font-bold text-indigo-700 disabled:text-slate-400"><Headphones size={15} />Nghe đoạn này</button>
            <label htmlFor="transcript-replacement" className="mt-3 block text-sm font-bold text-slate-800">Sau khi nghe, bạn xác nhận đã nói gì?</label>
            <input id="transcript-replacement" value={draft} onChange={event => setDraft(event.target.value)} maxLength={120} required disabled={saving || !onReviewDecision} placeholder="Nhập từ hoặc cụm từ bạn nghe được" className="mt-2 min-h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100" />
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="submit" disabled={saving || !draft.trim() || !onReviewDecision} className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-indigo-700 px-4 text-xs font-bold text-white hover:bg-indigo-800 disabled:opacity-40"><Check size={14} />{saving ? 'Đang lưu…' : 'Xác nhận cách ghi'}</button>
              {active.suggestion && <button type="button" onClick={() => save('dismissed')} disabled={saving || !onReviewDecision} className="min-h-10 rounded-xl border border-slate-200 bg-white px-4 text-xs font-bold text-slate-600">Giữ bản gốc</button>}
            </div>
            {error && <p role="alert" className="mt-3 text-sm text-rose-700">{error}</p>}
          </form>
        )}
        {saved && <p role="status" className="mt-4 text-xs leading-5 text-emerald-700">Đã lưu đối chiếu. Điểm hiện tại vẫn dựa trên bản ghi gốc.</p>}
        {review?.status === 'unavailable' && <p className="mt-4 text-xs text-slate-500">Chưa có gợi ý tự động. Chọn đoạn để nghe và đối chiếu.</p>}
      </div>

      <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-100 bg-slate-50/60 px-5 py-3 text-[11px] text-slate-500 sm:px-6">
        <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-amber-400" />Cần nghe lại</span>
        <span className="inline-flex items-center gap-1.5"><ArrowRight size={12} className="text-indigo-600" />Gợi ý, chưa phải lỗi được xác nhận</span>
        <span className="inline-flex items-center gap-1.5"><PencilLine size={12} />Chọn từ để đối chiếu</span>
      </footer>
    </section>
  );
}
