import React, { useState } from 'react';
import { X, Play, Save } from 'lucide-react';
import { useSpeech } from '../hooks/useSpeech.js';

export default function VoiceSetupModal({ initialText = "IELTS Speaking is a test of your English communication skills.", onSave, onClose }) {
  const { preview, stop } = useSpeech();
  const [selectedPreset, setSelectedPreset] = useState('US-Female');
  const [rate, setRate] = useState(1.0);
  
  const presets = [
    { id: 'US-Female', label: 'US Female (Mặc định)', desc: 'Giọng nữ chuẩn Mỹ, rõ ràng dễ nghe.' },
    { id: 'UK-Male', label: 'UK Male', desc: 'Giọng nam Anh Quốc trầm ấm.' },
    { id: 'AU-Female', label: 'AU Female', desc: 'Giọng nữ Úc với ngữ điệu đặc trưng.' },
  ];

  const handlePreview = (presetId) => {
    stop();
    preview(initialText, presetId, rate);
  };

  const handleSave = () => {
    localStorage.setItem('speaking_voice', JSON.stringify({ preset: selectedPreset, rate }));
    stop();
    if (onSave) onSave();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h2 className="text-xl font-bold text-gray-800">Cài đặt Giọng đọc AI</h2>
          <button onClick={() => { stop(); onClose(); }} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="space-y-3">
            <label className="text-sm font-bold text-gray-700">Chọn chất giọng</label>
            <div className="space-y-2">
              {presets.map(p => (
                <div 
                  key={p.id}
                  className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${selectedPreset === p.id ? 'border-blue-500 bg-blue-50/50' : 'border-gray-200 hover:border-blue-300'}`}
                  onClick={() => setSelectedPreset(p.id)}
                >
                  <div className="flex-1">
                    <p className={`font-semibold ${selectedPreset === p.id ? 'text-blue-700' : 'text-gray-800'}`}>{p.label}</p>
                    <p className="text-xs text-gray-500 mt-1">{p.desc}</p>
                  </div>
                  <button 
                    onClick={(e) => { e.stopPropagation(); handlePreview(p.id); }}
                    className="ml-4 p-2 rounded-full bg-white border border-gray-200 text-blue-600 hover:bg-blue-50 hover:border-blue-300 transition-all shadow-sm flex-shrink-0"
                    title="Nghe thử"
                  >
                    <Play className="w-4 h-4 fill-current" />
                  </button>
                </div>
              ))}
            </div>
            <p className="text-xs text-orange-500 mt-2 font-medium">Lưu ý: Chất giọng nam/nữ thực tế có thể thay đổi tuỳ thuộc vào trình duyệt và hệ điều hành của bạn.</p>
          </div>

          <div className="space-y-3">
            <label className="text-sm font-bold text-gray-700">Tốc độ đọc</label>
            <select 
              value={rate}
              onChange={(e) => setRate(parseFloat(e.target.value))}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 outline-none focus:border-blue-500"
            >
              <option value="0.75">0.75x (Chậm)</option>
              <option value="1">1.0x (Chuẩn)</option>
              <option value="1.25">1.25x (Nhanh)</option>
            </select>
          </div>
        </div>

        <div className="p-6 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
          <button 
            onClick={() => { stop(); onClose(); }}
            className="px-5 py-2.5 font-semibold text-gray-600 hover:bg-gray-200 rounded-xl transition-colors"
          >
            Hủy
          </button>
          <button 
            onClick={handleSave}
            className="px-5 py-2.5 font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-200 transition-all flex items-center gap-2"
          >
            <Save className="w-4 h-4" /> Lưu & Đọc
          </button>
        </div>
      </div>
    </div>
  );
}
