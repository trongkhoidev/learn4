import React from 'react';

export default function WordHighlighter({ words = [], onWordClick }) {
  const getWordColor = (score, color) => {
    if (color === 'gray') return 'text-gray-600 bg-gray-100 hover:bg-gray-200';
    if (score >= 80) return 'text-green-600 bg-green-50 hover:bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100';
    return 'text-red-600 bg-red-50 hover:bg-red-100 border border-red-100';
  };

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-bold text-gray-800 mb-4">Transcript & tín hiệu ASR</h3>
      <div className="flex flex-wrap gap-2 text-lg leading-relaxed">
        {words.map((wordObj, i) => (
          <button
            key={i} 
            type="button"
            disabled={!Number.isFinite(wordObj.start) || !Number.isFinite(wordObj.end)}
            onClick={() => onWordClick && onWordClick(wordObj)}
            className={`px-1.5 rounded transition-colors disabled:cursor-default ${getWordColor(wordObj.score, wordObj.color)} ${wordObj.uncertain ? 'ring-2 ring-amber-300' : ''}`}
            title={wordObj.uncertain ? `ASR cần nghe lại: ${wordObj.uncertainty_reason || 'uncertain span'}` : wordObj.color === 'gray' ? 'Nhà cung cấp STT không trả tín hiệu mức từ' : 'Tín hiệu nhận dạng ASR thô, chưa hiệu chuẩn'}
          >
            {wordObj.word}
          </button>
        ))}
      </div>
      <div className="mt-6 text-xs text-gray-500">
        Màu chỉ thể hiện tín hiệu nhận dạng ASR chưa hiệu chuẩn, không phải xác suất đúng hay điểm phát âm. Từ viền vàng cần nghe lại.
      </div>
    </div>
  );
}
