import { MapPin, Sparkles } from 'lucide-react';

export default function RecognitionContextField({ value, onChange, disabled }) {
  const terms = value.split(/[,;\n]/).map(term => term.trim()).filter(Boolean).slice(0, 40);
  return (
    <div className="mb-5 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
      <label htmlFor="recognition-context" className="flex items-center gap-2 text-sm font-bold text-slate-800">
        <MapPin size={16} className="text-indigo-600" aria-hidden="true" /> Tên riêng trong bài <span className="text-xs font-normal text-slate-400">Tuỳ chọn</span>
      </label>
      <textarea id="recognition-context" value={value} onChange={event => onChange(event.target.value)} disabled={disabled} maxLength={1200} rows={2}
        placeholder="Ví dụ: Quảng Trị, Đà Nẵng, Duy Tân University, React Native"
        aria-describedby="recognition-context-help"
        className="mt-3 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 disabled:opacity-50" />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs leading-5 text-slate-500">
        <p id="recognition-context-help" className="flex items-start gap-1.5"><Sparkles size={13} className="mt-1 shrink-0 text-indigo-500" />Tên người, địa danh, trường, công ty hoặc thuật ngữ bạn thực sự có thể nói. Phân cách bằng dấu phẩy hoặc xuống dòng.</p>
        <span className="font-semibold text-slate-400">{terms.length}/40 keyterms</span>
      </div>
      {terms.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5" aria-label="Keyterms nhận diện">{terms.slice(0, 8).map(term => <span key={term} className="rounded-full border border-indigo-100 bg-white px-2.5 py-1 text-[11px] font-semibold text-indigo-700">{term}</span>)}{terms.length > 8 && <span className="px-1 py-1 text-[11px] font-semibold text-slate-400">+{terms.length - 8}</span>}</div>}
    </div>
  );
}
