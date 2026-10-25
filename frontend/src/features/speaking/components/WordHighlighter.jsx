import React, { useState } from 'react';
import { Headphones, Check, X, Copy, Volume2, Sparkles } from 'lucide-react';

export default function WordHighlighter({
  words = [],
  transcript = '',
  review,
  onWordClick,
  onReviewDecision,
}) {
  const [active, setActive] = useState(null);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);

  // If words array is empty but transcript string exists, generate fallback word items
  const displayWords = (words && words.length > 0)
    ? words
    : (transcript || '').split(/\s+/).filter(Boolean).map((token, i) => ({
        id: `w${i + 1}`,
        word: token,
        color: 'green',
        score: 95,
        uncertain: false,
      }));

  const fullText = transcript || displayWords.map(w => w.word).join(' ');

  const suggestions = review?.suggestions || [];
  const suggestionByWordId = new Map();
  for (const item of suggestions) {
    for (const id of item.word_ids || []) {
      suggestionByWordId.set(id, item);
    }
  }

  function handleSelectWord(word) {
    const suggestion = suggestionByWordId.get(word.id);
    setActive({
      word_ids: suggestion ? suggestion.word_ids : [word.id],
      quote: word.word,
      suggestion,
      start: word.start,
      end: word.end,
    });
    setDraft(suggestion?.confirmed_text || suggestion?.replacement || word.word);
    setError('');
    setSaved(false);
    onWordClick?.(word);
  }

  async function handleSaveDecision(action) {
    if (!onReviewDecision || !active) return;
    setSaving(true);
    setError('');
    try {
      await onReviewDecision({
        word_ids: active.word_ids,
        replacement: draft.trim(),
        action,
      });
      setActive(null);
      setSaved(true);
    } catch (failure) {
      setError(failure.message || 'Chưa lưu được. Hãy thử lại.');
    } finally {
      setSaving(false);
    }
  }

  const handleCopyTranscript = async () => {
    if (!fullText) return;
    try {
      await navigator.clipboard.writeText(fullText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <section aria-label="Transcript bài nói và đối chiếu" className="overflow-hidden rounded-3xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-extrabold text-slate-900 sm:text-lg flex items-center gap-2">
            <Volume2 className="w-5 h-5 text-indigo-600" />
            Transcript bài nói (Nhận diện giọng nói)
          </h3>
          <p className="text-xs text-slate-500">
            Toàn bộ nội dung lời nói ghi nhận từ bản ghi âm. Bấm vào bất kỳ từ nào để nghe lại đoạn phát âm.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {fullText && (
            <button
              type="button"
              onClick={handleCopyTranscript}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-950 active:scale-95"
            >
              {copied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
              <span>{copied ? 'Đã sao chép' : 'Sao chép văn bản'}</span>
            </button>
          )}
        </div>
      </header>

      {/* Main transcript display: Every word is rendered clearly and naturally */}
      <div className="mt-5 rounded-2xl bg-slate-50/70 p-4 border border-slate-100/80 sm:p-6">
        <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-2 text-base leading-8 text-slate-800">
          {displayWords.map((word, index) => {
            const suggestion = suggestionByWordId.get(word.id);
            const hasSuggestion = Boolean(suggestion);
            const isUncertain = word.uncertain || (word.score != null && word.score < 60);

            return (
              <button
                key={word.id || index}
                type="button"
                onClick={() => handleSelectWord(word)}
                className={`inline-flex items-center rounded-lg px-1.5 py-0.5 text-left transition hover:bg-indigo-100 hover:text-indigo-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 active:scale-95 ${
                  hasSuggestion
                    ? 'border border-indigo-200 bg-indigo-50/60 font-semibold text-indigo-900'
                    : isUncertain
                    ? 'border-b-2 border-amber-400 bg-amber-50/40'
                    : 'text-slate-900 font-normal'
                }`}
                title={
                  hasSuggestion
                    ? `Gợi ý: ${suggestion.replacement || ''} — Bấm để nghe & xác nhận`
                    : 'Bấm để nghe đoạn phát âm từ này'
                }
              >
                <span>{word.word}</span>
                {hasSuggestion && (
                  <span className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-indigo-600" aria-hidden="true" />
                )}
              </button>
            );
          })}
          {!displayWords.length && (
            <p className="text-sm italic text-slate-400">Không có transcript cho bản ghi âm này.</p>
          )}
        </div>
      </div>

      {/* Word inspection sheet when a word is clicked */}
      {active && (
        <div className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50/30 p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                Từ đang chọn trong bài nói
              </p>
              <p className="mt-1 text-base font-extrabold text-slate-900">
                &ldquo;{active.quote}&rdquo;
              </p>
            </div>
            <button
              type="button"
              onClick={() => setActive(null)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-slate-700"
              title="Đóng"
            >
              <X size={16} />
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => onWordClick?.(active)}
              disabled={!Number.isFinite(active.start) || !Number.isFinite(active.end)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-white px-3 py-1.5 text-xs font-bold text-indigo-700 border border-indigo-200 shadow-xs hover:bg-indigo-50 active:scale-95 disabled:opacity-40"
            >
              <Headphones size={14} /> Nghe đoạn phát âm
            </button>

            {active.suggestion && (
              <span className="text-xs font-semibold text-slate-600">
                Gợi ý nhận diện:{' '}
                <strong className="text-indigo-800 font-bold">
                  {active.suggestion.replacement}
                </strong>
                {active.suggestion.reason_vi && ` (${active.suggestion.reason_vi})`}
              </span>
            )}
          </div>

          {active.suggestion && onReviewDecision && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSaveDecision('accepted');
              }}
              className="mt-3 pt-3 border-t border-indigo-100/70"
            >
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  maxLength={120}
                  placeholder="Nhập tên riêng hoặc từ bạn đã nói..."
                  className="min-h-9 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                />
                <button
                  type="submit"
                  disabled={saving || !draft.trim()}
                  className="inline-flex min-h-9 items-center gap-1.5 rounded-xl bg-indigo-700 px-3.5 text-xs font-bold text-white hover:bg-indigo-800 disabled:opacity-40"
                >
                  <Check size={13} /> {saving ? 'Đang lưu…' : 'Xác nhận tên riêng'}
                </button>
              </div>
              {error && <p className="mt-2 text-xs text-rose-600">{error}</p>}
            </form>
          )}

          {saved && (
            <p className="mt-2 text-xs font-semibold text-emerald-700">
              Đã cập nhật cách ghi tên riêng.
            </p>
          )}
        </div>
      )}

      <footer className="mt-4 flex flex-wrap items-center gap-4 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-indigo-600" /> Có gợi ý nhận diện tên riêng / địa danh
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Sparkles size={12} className="text-indigo-600" /> Bấm vào bất kỳ từ nào để nghe lại âm thanh
        </span>
      </footer>
    </section>
  );
}
