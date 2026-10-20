import React, { useState, useRef, useEffect } from 'react';
import { AlertCircle, CheckCircle2, Mic, Pause, Play, RotateCcw, Send, Square } from 'lucide-react';
import WaveSurfer from 'wavesurfer.js';

export default function AudioRecorderPro({ onRecordingComplete, disabled = false, maxSeconds = 180 }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [duration, setDuration] = useState(0);
  const [recordingError, setRecordingError] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const wavesurferRef = useRef(null);
  const containerRef = useRef(null);
  const timerRef = useRef(null);
  const chunksRef = useRef([]);
  const audioUrlRef = useRef(null);

  useEffect(() => {
    wavesurferRef.current = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#93c5fd',
      progressColor: '#2563eb',
      cursorColor: '#1d4ed8',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 60,
    });

    wavesurferRef.current.on('finish', () => setIsPlaying(false));

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      const recorder = mediaRecorderRef.current;
      if (recorder?.state && recorder.state !== 'inactive') {
        recorder.onstop = null;
        recorder.stop();
      }
      recorder?.stream?.getTracks().forEach(track => track.stop());
      wavesurferRef.current.destroy();
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  const startRecording = async () => {
    try {
      setRecordingError('');
      window.speechSynthesis?.cancel();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        chunksRef.current = [];

        if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
        const audioUrl = URL.createObjectURL(blob);
        audioUrlRef.current = audioUrl;
        wavesurferRef.current.load(audioUrl);
      };

      chunksRef.current = [];
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setDuration(0);
      
      timerRef.current = setInterval(() => {
        setDuration(prev => {
          if (prev + 1 >= maxSeconds) {
            setTimeout(stopRecording, 0);
          }
          return Math.min(prev + 1, maxSeconds);
        });
      }, 1000);
      
    } catch (err) {
      console.error("Error accessing microphone", err);
      const messages = {
        NotAllowedError: 'Trình duyệt chưa cho phép dùng microphone. Hãy cấp quyền rồi thử lại.',
        NotFoundError: 'Không tìm thấy microphone trên thiết bị này.',
        NotReadableError: 'Microphone đang được ứng dụng khác sử dụng. Hãy thử lại sau.',
      };
      setRecordingError(messages[err.name] || 'Không thể mở microphone. Hãy kiểm tra thiết bị và thử lại.');
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
      recorder.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const togglePlayback = () => {
    if (wavesurferRef.current && audioBlob) {
      wavesurferRef.current.playPause();
      setIsPlaying(wavesurferRef.current.isPlaying());
    }
  };

  const resetRecording = () => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setAudioBlob(null);
    setDuration(0);
    wavesurferRef.current.empty();
    setIsPlaying(false);
  };

  const submitRecording = () => {
    if (audioBlob && onRecordingComplete && !disabled) onRecordingComplete(audioBlob);
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-slate-50/80 p-4 sm:p-5">
      <div className="flex items-center gap-3 sm:gap-4">
        {!audioBlob ? (
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled}
            aria-label={isRecording ? 'Dừng ghi âm' : 'Bắt đầu ghi âm'}
            aria-pressed={isRecording}
            className={`grid h-14 w-14 shrink-0 place-items-center rounded-2xl transition focus-visible:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-50 ${isRecording ? 'bg-rose-600 text-white shadow-lg shadow-rose-900/20 ring-4 ring-rose-100 focus-visible:ring-rose-200' : 'bg-slate-950 text-white shadow-lg shadow-slate-900/15 hover:bg-blue-700 focus-visible:ring-blue-200'}`}
          >
            {isRecording ? <Square className="h-5 w-5 fill-current" /> : <Mic className="h-5 w-5" />}
          </button>
        ) : (
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={togglePlayback}
              aria-label={isPlaying ? 'Tạm dừng nghe lại' : 'Nghe lại bản ghi'}
              className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-blue-700 transition hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-100"
            >
              {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </button>
            <button
              type="button"
              onClick={resetRecording}
              aria-label="Ghi âm lại"
              className="grid h-12 w-12 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-200"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="flex min-w-0 items-center gap-2 text-sm font-bold text-slate-800" aria-live="polite">
              <span className={`h-2 w-2 shrink-0 rounded-full ${isRecording ? 'animate-pulse bg-rose-500' : audioBlob ? 'bg-emerald-500' : 'bg-slate-300'}`} />
              <span className="truncate">{isRecording ? 'Đang ghi âm...' : audioBlob ? 'Đã ghi âm xong' : 'Sẵn sàng ghi âm'}</span>
            </span>
            <span className={`shrink-0 font-mono text-sm font-bold tabular-nums ${isRecording ? 'text-rose-600' : 'text-slate-500'}`}>{formatTime(duration)}</span>
          </div>
          <div ref={containerRef} className="h-[54px] w-full overflow-hidden rounded-xl border border-slate-200/80 bg-white" />
        </div>
      </div>

      {recordingError && (
        <div role="alert" className="mt-3 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs leading-5 text-rose-800">
          <AlertCircle className="mt-0.5 shrink-0" size={15} /> <p>{recordingError}</p>
        </div>
      )}

      {audioBlob && (
        <div className="mt-4 rounded-xl border border-emerald-100 bg-white p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800"><CheckCircle2 size={15} /> Bản ghi đã sẵn sàng · nghe lại trước khi gửi</div>
          <button
            type="button"
            onClick={submitRecording}
            disabled={disabled}
            className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" /> {disabled ? 'Đang xử lý...' : 'Nộp bản ghi âm'}
          </button>
        </div>
      )}
      <p className="mt-3 text-center text-[11px] leading-5 text-slate-500">Thời lượng tối đa {Math.floor(maxSeconds / 60)} phút. Bạn có thể ghi âm lại trước khi nộp.</p>
    </div>
  );
}
