import { MapPin } from 'lucide-react';

export default function RecognitionContextField({ value, onChange, disabled }) {
  return (
    <div className="mb-5 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
      <label htmlFor="recognition-context" className="flex items-center gap-2 text-sm font-bold text-slate-800">
        <MapPin size={16} className="text-indigo-600" aria-hidden="true" /> Tên riêng trong bài <span className="text-xs font-normal text-slate-400">Tuỳ chọn</span>
      </label>
      <input id="recognition-context" value={value} onChange={event => onChange(event.target.value)} disabled={disabled} maxLength={400}
        placeholder="Ví dụ: Quảng Trị, Đà Nẵng, tên trường của bạn"
        aria-describedby="recognition-context-help"
        className="mt-3 min-h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 disabled:opacity-50" />
      <p id="recognition-context-help" className="mt-2 text-xs leading-5 text-slate-500">Giúp nhận diện tên người, địa danh hoặc thuật ngữ. Ngăn cách bằng dấu phẩy.</p>
    </div>
  );
}
