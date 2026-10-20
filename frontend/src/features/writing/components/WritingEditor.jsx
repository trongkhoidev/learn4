import { useState } from "react";

export default function WritingEditor({ onEssayChange, onImageChange, minWords = 250 }) {
  const [essay, setEssay] = useState("");
  const words = essay.trim() ? essay.trim().split(/\s+/).length : 0;

  function handleChange(e) {
    setEssay(e.target.value);
    onEssayChange && onEssayChange(e.target.value);
  }

  function handleImage(e) {
    const file = e.target.files?.[0];
    if (file) onImageChange && onImageChange(file);
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all">
      <div className="bg-slate-50 border-b border-slate-200 px-4 py-2 flex justify-between items-center">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <span className="text-blue-600">✍️</span> Bài làm của bạn
        </h3>
        <label className="cursor-pointer inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors shadow-sm">
          <span>📎</span> Chụp ảnh bài viết
          <input type="file" accept="image/*" className="hidden" onChange={handleImage} />
        </label>
      </div>
      
      <textarea
        className="w-full flex-1 min-h-[300px] border-none p-5 text-slate-700 leading-relaxed resize-y focus:ring-0 focus:outline-none bg-transparent placeholder-slate-400"
        placeholder="Bắt đầu viết bài của bạn tại đây..."
        value={essay}
        onChange={handleChange}
        spellCheck="false"
      />
      
      <div className="bg-slate-50 border-t border-slate-200 px-5 py-3 flex justify-between items-center text-sm">
        <div className="flex items-center gap-2">
          <div className={`flex items-center justify-center h-6 px-2.5 rounded-full font-bold text-xs ${words >= minWords ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
            {words} {words >= minWords ? '✓' : ''}
          </div>
          <span className="text-slate-500 font-medium">/ {minWords} từ (tối thiểu)</span>
        </div>
        
        {words > 0 && words < minWords && (
          <span className="text-orange-500 text-xs font-medium animate-pulse">
            Bạn cần viết thêm {minWords - words} từ nữa
          </span>
        )}
      </div>
    </div>
  );
}
