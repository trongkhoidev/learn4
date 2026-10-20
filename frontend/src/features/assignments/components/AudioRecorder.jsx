import { useEffect, useRef, useState } from "react";

export default function AudioRecorder({ onReady }) {
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => () => clearInterval(timerRef.current), []);

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    chunksRef.current = [];
    const rec = new MediaRecorder(stream);
    recorderRef.current = rec;
    rec.ondataavailable = (e) => chunksRef.current.push(e.data);
    rec.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
      setPreviewUrl(URL.createObjectURL(blob));
      onReady && onReady(blob);
    };
    rec.start();
    setRecording(true);
    setSeconds(0);
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
  }

  function stop() {
    recorderRef.current?.stop();
    setRecording(false);
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <div className="flex flex-col items-center gap-4 bg-slate-50 p-6 rounded-xl border border-slate-200">
      <div className="text-center mb-2">
        <h3 className="font-semibold text-slate-700">Phần ghi âm</h3>
        <p className="text-sm text-slate-500">Vui lòng nói rõ ràng vào micro</p>
      </div>
      
      {recording ? (
        <div className="flex flex-col items-center gap-4 w-full">
          <div className="flex items-center justify-center gap-3 bg-red-50 text-red-700 py-3 px-6 rounded-full border border-red-200 w-fit">
            <span className="h-4 w-4 animate-pulse rounded-full bg-red-600 shadow-[0_0_8px_rgba(220,38,38,0.6)]" />
            <span className="font-mono text-xl font-bold tracking-wider">
              {mm}:{ss}
            </span>
          </div>
          
          {/* Audio visualizer mockup */}
          <div className="flex items-center justify-center gap-1 h-12 w-full px-4">
            {Array.from({ length: 24 }).map((_, i) => (
              <div 
                key={i} 
                className="w-1.5 bg-red-400 rounded-full animate-pulse" 
                style={{
                  height: `${Math.max(10, Math.random() * 100)}%`,
                  animationDelay: `${Math.random() * 0.5}s`,
                  animationDuration: `${0.5 + Math.random() * 0.5}s`
                }}
              />
            ))}
          </div>

          <button 
            onClick={stop} 
            className="flex items-center gap-2 rounded-full bg-red-600 px-8 py-3 text-white font-bold shadow-md hover:bg-red-700 hover:shadow-lg transition-all active:scale-95"
          >
            <span className="text-xl">⏹</span> Dừng ghi âm
          </button>
        </div>
      ) : (
        <button 
          onClick={start} 
          className="flex items-center gap-3 rounded-full bg-blue-600 px-8 py-4 text-white font-bold shadow-md hover:bg-blue-700 hover:shadow-lg transition-all active:scale-95 group"
        >
          <span className="text-2xl group-hover:scale-110 transition-transform">🎙️</span> 
          <span>Bắt đầu ghi âm</span>
        </button>
      )}
      
      {previewUrl && !recording && (
        <div className="w-full mt-4 space-y-2">
          <p className="text-sm font-medium text-slate-600 text-center">Bản ghi nghe thử:</p>
          <audio controls src={previewUrl} className="w-full" />
          <p className="text-xs text-center text-slate-400">Nếu chưa ưng ý, bạn có thể ghi âm lại.</p>
        </div>
      )}
    </div>
  );
}
