import { useMockController } from '../hooks/useMockController.js';
import {
  AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, ClipboardCheck, Clock3, Mic2, Sparkles,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import AudioRecorderPro from '../components/AudioRecorderPro.jsx';
import ScoreGrid from '../components/ScoreGrid.jsx';
import SpeakButton from '../components/SpeakButton.jsx';

export default function SpeakingMockTest() {
  const { testId } = useParams();
  const studentName = localStorage.getItem('speaking_name') || 'Guest';
  const {
    questions, session, turnIndex, isEvaluating, error, mockResult, prepStarted,
    startPreparation, prepRemaining, current, part, totalTurns, progress, handleRecordingComplete,
  } = useMockController(testId, studentName);

  if (!questions || !session) {
    return (
      <div className="mx-auto max-w-3xl py-8">
        {error ? (
          <div role="alert" className="rounded-[26px] border border-rose-200 bg-white p-6 shadow-sm sm:p-8">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-rose-50 text-rose-700"><AlertCircle size={22} /></span>
            <h1 className="mt-5 text-2xl font-extrabold text-slate-950">Chưa thể tạo bài thi thử</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">{error}</p>
            <Link to="/speaking" className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white hover:bg-blue-700">Quay về tổng quan <ArrowRight size={16} /></Link>
          </div>
        ) : (
          <div role="status" className="rounded-[26px] border border-slate-200 bg-white p-8 text-center shadow-sm">
            <span className="mx-auto grid h-12 w-12 animate-pulse place-items-center rounded-2xl bg-blue-50 text-blue-700"><Mic2 size={22} /></span>
            <h1 className="mt-4 text-xl font-bold text-slate-900">Đang chuẩn bị đề thi...</h1>
            <p className="mt-1 text-sm text-slate-500">Đang tải câu hỏi và tạo phiên luyện tập của bạn.</p>
          </div>
        )}
      </div>
    );
  }

  if (mockResult) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="rounded-[26px] bg-gradient-to-br from-[#111b3d] to-[#263c82] p-6 text-white shadow-lg sm:p-8">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-400/15 text-emerald-200"><CheckCircle2 size={24} /></span>
          <p className="mt-5 text-xs font-bold uppercase tracking-[.16em] text-blue-200">Mock Test · {questions.topic.name}</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Hoàn Thành Mock Test</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-blue-100/75">Đánh giá gộp evidence từ cả ba Part. Tiêu chí chưa đủ bằng chứng sẽ không có band.</p>
        </div>
        <ScoreGrid scores={mockResult} />
        <div className="flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3.5 text-sm leading-6 text-blue-950/80">
          <Sparkles className="mt-0.5 shrink-0 text-blue-700" size={17} />
          <p>Đây là kết quả chẩn đoán để luyện tập, không phải điểm IELTS chính thức. {session.result?.pronun?.reason || ''}</p>
        </div>
        <div className="flex flex-col gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:justify-between">
          <Link to="/speaking" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 text-sm font-bold text-slate-700">Tổng quan</Link>
          <Link to="/speaking/history" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-bold text-white hover:bg-blue-700">Xem lịch sử <ArrowRight size={16} /></Link>
        </div>
      </div>
    );
  }

  const recorderReady = part !== 2 || (prepStarted && prepRemaining === 0);
  const partName = part === 1 ? 'Introduction & interview' : part === 2 ? 'Long turn' : 'Discussion';

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link to="/speaking" className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-blue-700"><ArrowLeft size={16} /> Quay lại Dashboard</Link>

      {error && <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm leading-6 text-rose-800"><AlertCircle className="mt-0.5 shrink-0" size={18} /><p>{error}</p></div>}

      <header className="flex flex-col justify-between gap-5 rounded-[26px] bg-gradient-to-br from-[#111b3d] via-[#1c2d61] to-[#3642a0] p-6 text-white shadow-lg shadow-blue-950/10 sm:flex-row sm:items-end sm:p-8">
        <div>
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.16em] text-blue-200"><ClipboardCheck size={14} aria-hidden="true" /> Thi thử · {questions.topic.name}</p>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Mock Test — {questions.topic.name}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100/75">Đi lần lượt qua ba phần. Câu trả lời được lưu trong phiên để tổng hợp sau cùng.</p>
        </div>
        <div className="w-fit rounded-2xl border border-white/10 bg-white/[0.08] px-4 py-3">
          <p className="text-xs font-semibold text-blue-100/70">Câu hiện tại</p>
          <p className="mt-1 text-lg font-extrabold">{turnIndex + 1}<span className="mx-1 text-blue-200/50">/</span>{totalTurns}</p>
        </div>
      </header>

      <section aria-label="Tiến độ bài thi" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:px-5">
        <div className="mb-2 flex items-center justify-between gap-3 text-xs font-bold">
          <span className="text-slate-600">Part {part} · {partName}</span><span className="text-blue-700">{progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-gradient-to-r from-blue-600 to-violet-600 transition-[width] duration-500" style={{ width: `${progress}%` }} /></div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {[1, 2, 3].map(number => (
            <div key={number} className={`flex items-center justify-center gap-2 rounded-xl px-2 py-2 text-[11px] font-bold ${number === part ? 'bg-blue-50 text-blue-800' : number < part ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-50 text-slate-400'}`}>
              {number < part ? <CheckCircle2 size={14} /> : <span className="grid h-5 w-5 place-items-center rounded-full bg-white/80">{number}</span>}
              <span>Part {number}</span>
            </div>
          ))}
        </div>
      </section>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,.85fr)]">
        <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex items-center justify-between gap-3">
            <span className="rounded-full bg-blue-50 px-3 py-1.5 text-[11px] font-extrabold uppercase tracking-wider text-blue-700">Part {part}</span>
            <span className="inline-flex items-center gap-2 rounded-full bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-500"><Clock3 size={14} />{part === 2 ? '1 phút chuẩn bị · nói tối đa 2 phút' : 'Trả lời tự nhiên'}</span>
          </div>
          <div className="mt-8 flex items-start gap-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-950 text-sm font-extrabold text-white">{String(turnIndex + 1).padStart(2, '0')}</span>
            <div className="min-w-0 flex-1">
              <p className="mb-2 text-xs font-semibold text-slate-400">Câu hỏi {turnIndex + 1} trong phiên thi</p>
              <div className="flex items-start gap-2"><h2 className="text-xl font-bold leading-8 tracking-tight text-slate-950 sm:text-2xl">{current.question_text}</h2><SpeakButton text={current.question_text} /></div>
            </div>
          </div>
          {part === 2 && current.cue_card && <div className="mt-6 rounded-2xl border border-violet-100 bg-violet-50/70 p-4 text-sm leading-6 text-slate-700"><p className="mb-2 text-xs font-bold uppercase tracking-wider text-violet-800">Cue card</p><p className="whitespace-pre-line">{current.cue_card}</p></div>}
        </section>

        <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Mic2 size={19} /></span>
            <div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-emerald-700">Phần trả lời</p><h2 className="mt-1 text-lg font-bold text-slate-950">{part === 2 ? 'Chuẩn bị và ghi âm' : 'Ghi âm câu trả lời'}</h2></div>
          </div>

          {part === 2 && !recorderReady && (
            <div className="mb-4 rounded-2xl border border-violet-100 bg-violet-50/70 p-5 text-center">
              <p className="text-xs font-bold uppercase tracking-wider text-violet-700">Thời gian chuẩn bị</p>
              <p className="mt-2 font-mono text-5xl font-extrabold tabular-nums tracking-tight text-violet-950" aria-live="polite">{prepStarted ? `00:${String(prepRemaining).padStart(2, '0')}` : '01:00'}</p>
              {!prepStarted ? (
                <button type="button" onClick={startPreparation} className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-violet-700 px-4 text-sm font-bold text-white transition hover:bg-violet-800">Bắt đầu 1 phút chuẩn bị <ArrowRight size={16} /></button>
              ) : <p className="mt-3 text-xs leading-5 text-violet-900/70">Ghi âm sẽ mở tự động khi hết giờ. Hãy ghi ý chính.</p>}
            </div>
          )}

          {recorderReady && <AudioRecorderPro key={current.id} onRecordingComplete={handleRecordingComplete} disabled={isEvaluating} maxSeconds={part === 2 ? 120 : 90} />}
          {isEvaluating && <div role="status" className="mt-4 flex items-center gap-3 rounded-xl bg-blue-50 p-3 text-sm font-semibold text-blue-900"><span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-200 border-t-blue-700" />Đang xử lý câu trả lời…</div>}
          <p className="mt-4 text-xs leading-5 text-slate-500">Bạn có thể nghe lại bản ghi trước khi nộp. Câu tiếp theo sẽ mở sau khi câu hiện tại được lưu.</p>
        </section>
      </div>
    </div>
  );
}
