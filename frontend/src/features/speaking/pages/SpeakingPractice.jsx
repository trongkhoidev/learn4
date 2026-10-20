import { useEffect, useRef } from 'react';
import { usePracticeController } from '../hooks/usePracticeController.js';
import AudioRecorderPro from '../components/AudioRecorderPro.jsx';
import ScoreGrid from '../components/ScoreGrid.jsx';
import WordHighlighter from '../components/WordHighlighter.jsx';
import GrammarErrorList from '../components/GrammarErrorList.jsx';
import PronunErrorList from '../components/PronunErrorList.jsx';
import FeedbackFocusCard from '../components/FeedbackFocusCard.jsx';
import SpeakButton from '../components/SpeakButton.jsx';
import {
  AlertCircle, ArrowLeft, ArrowRight, BookOpen, CheckCircle2, ChevronLeft,
  ChevronRight, Clock3, Mic2, Sparkles,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

export default function SpeakingPractice() {
  const { topicId: routeTopicId } = useParams();
  const {
    step, setStep, topics, selectedTopic, setSelectedTopic, selectedPart, setSelectedPart,
    isEvaluating, result, setResult, questions, questionsLoading, questionIndex, setQuestionIndex, error,
    setError, prepStarted, startPreparation, resetPreparation, prepRemaining, recordingUrl,
    currentQuestion, displayedQuestion, isPart2, recorderReady, handleRecordingComplete,
  } = usePracticeController(routeTopicId);
  const audioRef = useRef(null);
  const playbackStopRef = useRef(null);

  useEffect(() => {
    return () => {
      if (recordingUrl?.startsWith('blob:')) URL.revokeObjectURL(recordingUrl);
    };
  }, [recordingUrl]);

  const playWord = (word) => {
    const audio = audioRef.current;
    if (!audio || !Number.isFinite(word?.start) || !Number.isFinite(word?.end)) return;
    const duration = audio.duration;
    if (!Number.isFinite(duration) || duration <= 0) return;
    const from = Math.max(0, Math.min(duration, word.start - 0.15));
    const to = Math.max(from, Math.min(duration, word.end + 0.2));
    audio.pause();
    if (playbackStopRef.current) {
      audio.removeEventListener('timeupdate', playbackStopRef.current);
      playbackStopRef.current = null;
    }
    audio.currentTime = from;
    const stopAtWordEnd = () => {
      if (audio.currentTime >= to) {
        audio.pause();
        audio.removeEventListener('timeupdate', stopAtWordEnd);
        playbackStopRef.current = null;
      }
    };
    playbackStopRef.current = stopAtWordEnd;
    audio.addEventListener('timeupdate', stopAtWordEnd);
    audio.play().catch(() => {
      audio.removeEventListener('timeupdate', stopAtWordEnd);
      playbackStopRef.current = null;
    });
  };

  const partDetails = {
    'PART 1': { title: 'Introduction & interview', detail: 'Trả lời tự nhiên, rõ ý và đi thẳng vào câu hỏi.' },
    'PART 2': { title: 'Long turn', detail: 'Một phút chuẩn bị, sau đó nói tối đa hai phút.' },
    'PART 3': { title: 'Discussion', detail: 'Phát triển quan điểm và giải thích lý do của bạn.' },
  }[selectedPart];

  return (
    <div className="space-y-6">
      <Link to="/speaking" className="inline-flex min-h-10 items-center gap-2 rounded-lg text-sm font-semibold text-slate-500 transition hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
        <ArrowLeft size={16} aria-hidden="true" /> Quay lại Dashboard
      </Link>

      {error && (
        <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm leading-6 text-rose-800">
          <AlertCircle className="mt-0.5 shrink-0 text-rose-600" size={18} aria-hidden="true" />
          <p>{error}</p>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-6">
          <header className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#111b3d] via-[#1c2d61] to-[#3642a0] px-6 py-7 text-white sm:px-9 sm:py-9">
            <div aria-hidden="true" className="pointer-events-none absolute -right-14 -top-24 h-64 w-64 rounded-full border-[34px] border-white/[0.06]" />
            <div className="relative flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
              <div className="max-w-2xl">
                <p className="mb-3 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.16em] text-blue-200"><BookOpen size={14} /> Practice · theo chủ đề</p>
                <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Chọn chủ đề để bắt đầu</h1>
                <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100/75 sm:text-base">Luyện từng câu hỏi theo Part. Bạn có thể nghe lại bản ghi và xem phản hồi sau khi nộp.</p>
              </div>
              <div className="flex w-fit items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.08] px-4 py-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/10"><Sparkles size={19} /></span>
                <span><span className="block text-xl font-extrabold">{topics.length}</span><span className="block text-[11px] text-blue-100/70">chủ đề sẵn có</span></span>
              </div>
            </div>
          </header>

          {topics.length > 0 ? (
            <div className={`grid gap-4 sm:grid-cols-2 ${topics.length <= 2 ? 'xl:grid-cols-2' : 'xl:grid-cols-3'}`}>
              {topics.map((topic, index) => (
                <button
                  type="button"
                  key={topic.id}
                  onClick={() => { setSelectedTopic(topic); setStep(2); setError(''); }}
                  className="group flex min-h-48 flex-col justify-between rounded-[24px] border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-950/[0.06] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-100 sm:p-6"
                >
                  <span className="flex w-full items-start justify-between">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-blue-700 transition group-hover:bg-blue-600 group-hover:text-white"><BookOpen size={21} aria-hidden="true" /></span>
                    <span className="rounded-full bg-slate-50 px-3 py-1 text-[11px] font-bold tracking-wider text-slate-400">{String(index + 1).padStart(2, '0')}</span>
                  </span>
                  <span className="mt-7 block">
                    <span className="mb-1 block text-[10px] font-bold uppercase tracking-[.16em] text-blue-700">Chủ đề luyện nói</span>
                    <h3 className="font-bold text-slate-950 text-xl">{topic.name}</h3>
                    <span className="mt-2 flex items-end justify-between gap-3 text-sm leading-5 text-slate-500">
                      <span className="line-clamp-2">{topic.description || 'Các câu hỏi Speaking theo chủ đề.'}</span>
                      <ArrowRight className="mb-0.5 shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-blue-600" size={18} aria-hidden="true" />
                    </span>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
              <BookOpen className="mx-auto text-slate-300" size={28} />
              <h2 className="mt-4 text-lg font-bold text-slate-900">Chưa có chủ đề luyện tập</h2>
              <p className="mt-1 text-sm text-slate-500">Thử tải lại sau hoặc quay về tổng quan.</p>
            </div>
          )}
        </div>
      )}

      {step === 2 && selectedTopic && (
        <div className="space-y-5">
          <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.16em] text-blue-700"><Mic2 size={14} /> Luyện theo chủ đề</p>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-950">{selectedTopic.name}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">{selectedTopic.description}</p>
            </div>
            <button type="button" onClick={() => { setSelectedTopic(null); setStep(1); setError(''); }} className="inline-flex min-h-10 items-center gap-2 self-start rounded-xl border border-slate-200 bg-white px-3.5 text-sm font-semibold text-slate-600 transition hover:border-blue-200 hover:text-blue-700 sm:self-auto">
              <ArrowLeft size={15} aria-hidden="true" /> Đổi chủ đề
            </button>
          </header>

          <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,.85fr)]">
            <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-5 pt-5 sm:px-7 sm:pt-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">Chọn phần thi</p>
                    <p className="mt-1 text-sm font-semibold text-slate-700">{partDetails.title}</p>
                  </div>
                  {questions.length > 0 && <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-600">Câu {questionIndex + 1} / {questions.length}</span>}
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2" role="tablist" aria-label="Phần thi IELTS Speaking">
                  {['PART 1', 'PART 2', 'PART 3'].map((part, index) => {
                    const active = selectedPart === part;
                    return (
                      <button
                        type="button"
                        role="tab"
                        aria-selected={active}
                        key={part}
                        onClick={() => setSelectedPart(part)}
                        className={`min-h-11 rounded-t-xl border-b-2 px-2 text-xs font-extrabold transition sm:text-sm ${active ? 'border-blue-600 bg-blue-50/80 text-blue-800' : 'border-transparent text-slate-400 hover:bg-slate-50 hover:text-slate-700'}`}
                      >
                        <span className="block">PART {index + 1}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="p-5 sm:p-7">
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-blue-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-blue-600" /> {selectedPart}
                  </span>
                  {questions.length > 1 && (
                    <div className="flex items-center gap-1.5">
                      <button type="button" aria-label="Câu trước" disabled={questionIndex === 0} onClick={() => setQuestionIndex(index => Math.max(0, index - 1))} className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-35"><ChevronLeft size={17} /></button>
                      <button type="button" aria-label="Câu tiếp theo" disabled={questionIndex >= questions.length - 1} onClick={() => setQuestionIndex(index => Math.min(questions.length - 1, index + 1))} className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-35"><ChevronRight size={17} /></button>
                    </div>
                  )}
                </div>

                <div className="my-7 flex items-start gap-3 sm:gap-4">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-950 text-sm font-extrabold text-white">{String(questionIndex + 1).padStart(2, '0')}</span>
                  <div className="min-w-0 flex-1">
                    <p className="mb-2 text-xs font-semibold text-slate-400">Câu hỏi hiện tại</p>
                    <div className="flex items-start gap-2">
                      <h2 className="text-xl font-bold leading-8 tracking-tight text-slate-950 sm:text-2xl">{displayedQuestion}</h2>
                      <SpeakButton text={displayedQuestion} />
                    </div>
                  </div>
                </div>

                {isPart2 && (
                  <div className="rounded-2xl border border-violet-100 bg-violet-50/70 p-4 sm:p-5">
                    <div className="flex items-center gap-2 text-sm font-bold text-violet-900"><Clock3 size={17} /> 1 phút chuẩn bị · nói tối đa 2 phút</div>
                    {currentQuestion?.cue_card ? (
                      <p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-700">{currentQuestion.cue_card}</p>
                    ) : (
                      <p className="mt-3 text-sm leading-6 text-slate-600">Ghi nhanh một vài ý chính trước khi bắt đầu phần nói dài.</p>
                    )}
                  </div>
                )}

                {questions.length > 1 && (
                  <div className="mt-6 flex flex-wrap items-center gap-2" aria-label="Chọn câu hỏi">
                    {questions.map((question, index) => (
                      <button
                        type="button"
                        key={question.id || index}
                        aria-label={`Câu ${index + 1}`}
                        aria-current={index === questionIndex ? 'step' : undefined}
                        onClick={() => setQuestionIndex(index)}
                        className={`grid h-9 w-9 place-items-center rounded-xl text-xs font-bold transition ${index === questionIndex ? 'bg-slate-950 text-white shadow-sm' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
                      >{index + 1}</button>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="mb-5 flex items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Mic2 size={19} aria-hidden="true" /></span>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[.16em] text-emerald-700">Bước tiếp theo</p>
                  <h2 className="mt-1 text-lg font-bold text-slate-950">{isPart2 ? 'Chuẩn bị rồi ghi âm' : 'Ghi âm câu trả lời'}</h2>
                  <p className="mt-1 text-sm leading-5 text-slate-500">{partDetails.detail}</p>
                </div>
              </div>

              {questionsLoading && <p role="status" className="py-6 text-center text-sm text-slate-500">Đang tải câu hỏi…</p>}

              {isPart2 && !questionsLoading && !recorderReady && (
                <div className="mb-4 rounded-2xl border border-violet-100 bg-violet-50/70 p-5 text-center">
                  <p className="text-xs font-bold uppercase tracking-wider text-violet-700">Thời gian chuẩn bị</p>
                  <p className="mt-2 font-mono text-5xl font-extrabold tabular-nums tracking-tight text-violet-950" aria-live="polite">
                    {prepStarted ? `00:${String(prepRemaining).padStart(2, '0')}` : '01:00'}
                  </p>
                  <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-violet-100">
                    <div className="h-full rounded-full bg-violet-600 transition-[width] duration-1000" style={{ width: `${prepStarted ? ((60 - prepRemaining) / 60) * 100 : 0}%` }} />
                  </div>
                  {!prepStarted ? (
                    <button type="button" onClick={startPreparation} className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-violet-700 px-4 text-sm font-bold text-white transition hover:bg-violet-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-violet-200">
                      Bắt đầu 1 phút chuẩn bị <ArrowRight size={16} />
                    </button>
                  ) : (
                    <p className="mt-4 text-xs leading-5 text-violet-900/70">Ghi âm sẽ mở tự động khi hết giờ. Hãy ghi nhớ ý chính, không cần viết thành câu.</p>
                  )}
                </div>
              )}

              {recorderReady && (
                <AudioRecorderPro
                  key={`${currentQuestion?.id || displayedQuestion}-${selectedPart}`}
                  onRecordingComplete={handleRecordingComplete}
                  disabled={isEvaluating}
                  maxSeconds={isPart2 ? 120 : 90}
                />
              )}

              <div className="mt-4 flex items-start gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-xs leading-5 text-slate-500">
                <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-600" size={15} aria-hidden="true" />
                <p>Bạn có thể nghe lại và ghi âm lại trước khi gửi câu trả lời.</p>
              </div>
            </section>
          </div>

          {isEvaluating && (
            <div role="status" className="flex items-center gap-4 rounded-2xl border border-blue-100 bg-blue-50 px-5 py-4 text-blue-950">
              <span className="h-9 w-9 animate-spin rounded-full border-[3px] border-blue-200 border-t-blue-700" />
              <span><span className="block text-sm font-bold">Đang xử lý bài ghi âm</span><span className="mt-0.5 block text-xs text-blue-800/70">Bạn có thể chờ tại trang này; kết quả sẽ hiện khi hoàn tất.</span></span>
            </div>
          )}
        </div>
      )}

      {step === 3 && result && (
        <div className="space-y-6">
          <header className="flex flex-col justify-between gap-4 rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:p-7">
            <div>
              <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.15em] text-blue-700"><Sparkles size={14} /> Kết quả luyện tập</p>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-950">Kết Quả Phân Tích</h1>
              <p className="mt-2 text-sm text-slate-500">{selectedTopic?.name} <span className="mx-1 text-slate-300">/</span> {selectedPart}</p>
            </div>
            <span className={`w-fit rounded-full px-3.5 py-2 text-xs font-bold ${result.raw.status === 'scored' ? 'bg-emerald-50 text-emerald-800' : result.raw.status === 'needs_review' ? 'bg-amber-50 text-amber-800' : 'bg-slate-100 text-slate-700'}`}>
              {result.raw.status === 'scored' ? 'Đủ bằng chứng' : result.raw.status === 'needs_review' ? 'Cần nghe lại' : result.raw.status}
            </span>
          </header>

          <ScoreGrid scores={result.scores} />

          {result.raw.status !== 'scored' && (
            <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-amber-950">
              <AlertCircle className="mt-0.5 shrink-0 text-amber-700" size={19} aria-hidden="true" />
              <div><h2 className="font-bold">{result.raw.status === 'needs_review' ? 'Bài nói cần được xem lại' : 'Chỉ hiển thị tiêu chí đủ bằng chứng'}</h2>
                <p className="mt-1 text-sm leading-6 text-amber-900/80">{(result.raw.status === 'failed' ? result.raw.fluency?.feedback : result.raw.pronun?.feedback) || 'Một số tiêu chí chưa có đủ bằng chứng để ước lượng band. Xem phản hồi và bước luyện tiếp theo bên dưới.'}</p>
                {!!result.raw.review_reasons?.length && <p className="mt-2 text-xs leading-5 text-amber-900/70">Mã review: {result.raw.review_reasons.join(' · ')}</p>}
              </div>
            </div>
          )}

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,.85fr)]">
            <section className="space-y-4">
              {recordingUrl && (
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Bản ghi của bạn</p>
                  <audio ref={audioRef} controls src={recordingUrl} className="w-full" />
                </div>
              )}
              <WordHighlighter words={result.words} onWordClick={playWord} />
            </section>
            <GrammarErrorList errors={result.errors} status={result.raw.grammar?.status} />
          </div>

          <section aria-label="Phản hồi theo tiêu chí" className="grid gap-4 md:grid-cols-2">
            {[
              ['fluency', 'Fluency & Coherence', 'text-blue-700'],
              ['vocab', 'Lexical Resource', 'text-violet-700'],
              ['grammar', 'Grammatical Range and Accuracy', 'text-emerald-700'],
              ['pronun', 'Pronunciation', 'text-amber-700'],
            ].map(([key, label, color]) => {
              const criterion = result.raw[key];
              return (
                <article key={key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                  <h3 className={`text-[10px] font-bold uppercase tracking-[.15em] ${color}`}>{label}</h3>
                  <FeedbackFocusCard comment={criterion?.feedback || 'Chưa có phản hồi đủ bằng chứng cho tiêu chí này.'} />
                  {criterion?.next_action_vi && (
                    <div className="mt-4 rounded-xl bg-blue-50 p-3 text-sm leading-6 text-blue-950">
                      <p className="font-bold">Bước luyện tiếp theo</p>
                      <p className="mt-1">{criterion.next_action_vi}</p>
                    </div>
                  )}
                </article>
              );
            })}
          </section>

          <PronunErrorList problems={result.raw.pronun?.problem_words || []} />
          <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:justify-between">
            <button type="button" onClick={() => { setStep(2); setResult(null); resetPreparation(); }} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
              <ArrowLeft size={16} /> Thử lại chủ đề này
            </button>
            <button type="button" onClick={() => { setSelectedTopic(null); setStep(1); setResult(null); }} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-bold text-white transition hover:bg-blue-700">
              Luyện chủ đề khác <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
