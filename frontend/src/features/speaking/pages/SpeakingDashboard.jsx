import * as speakingApi from '../api.js';
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight, BookOpen, Clock3, Flame, Headphones, History, Mic2,
  Play, Sparkles, Volume2,
} from 'lucide-react';

export default function SpeakingDashboard() {
  const [progress, setProgress] = useState(null);
  const [studentName, setStudentName] = useState(localStorage.getItem('speaking_name') || '');
  const [isNameSet, setIsNameSet] = useState(!!localStorage.getItem('speaking_name'));
  const [loading, setLoading] = useState(false);

  const handleSetName = event => {
    event.preventDefault();
    const name = studentName.trim();
    if (!name) return;
    localStorage.setItem('speaking_name', name);
    setStudentName(name);
    setIsNameSet(true);
  };

  useEffect(() => {
    if (!isNameSet) return undefined;
    let active = true;
    setLoading(true);
    speakingApi.getSpeakingProgress(studentName)
      .then(value => { if (active) setProgress(value); })
      .catch(error => {
        if (!active) return;
        console.error(error);
        setProgress(null);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isNameSet, studentName]);

  if (!isNameSet) {
    return (
      <div className="grid min-h-[68vh] items-center gap-10 py-4 lg:grid-cols-[1.1fr_.9fr] lg:gap-16">
        <section className="max-w-xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-[.14em] text-blue-700 shadow-sm">
            <Sparkles size={14} aria-hidden="true" /> Speaking studio
          </div>
          <h1 className="text-4xl font-extrabold leading-[1.08] tracking-tight text-slate-950 sm:text-5xl">
            Nói tự nhiên hơn,
            <span className="mt-2 block bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">từng câu một.</span>
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-600 sm:text-lg">
            Luyện theo chủ đề hoặc làm bài thi thử. Nghe lại câu trả lời, xem transcript và nhận phản hồi có nêu rõ phần nào đủ bằng chứng.
          </p>
          <div className="mt-8 grid gap-3 text-sm text-slate-600">
            <div className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-xl bg-blue-50 text-blue-700"><BookOpen size={16} /></span>Chọn từng Part và câu hỏi phù hợp</div>
            <div className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-xl bg-violet-50 text-violet-700"><Headphones size={16} /></span>Nghe lại bản ghi và đối chiếu transcript</div>
            <div className="flex items-center gap-3"><span className="grid h-8 w-8 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Volume2 size={16} /></span>Band được để trống khi chưa đủ căn cứ</div>
          </div>
        </section>

        <form onSubmit={handleSetName} className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/[0.04] sm:p-9">
          <div className="mb-6 grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 to-violet-600 text-white shadow-lg shadow-blue-900/15">
            <Mic2 size={24} aria-hidden="true" />
          </div>
          <p className="text-xs font-bold uppercase tracking-[.16em] text-blue-700">Bắt đầu hành trình</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Bạn muốn được gọi là gì?</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">Tên này dùng để lưu và hiển thị lịch sử luyện tập trên thiết bị của bạn.</p>
          <label htmlFor="speaking-name" className="mb-2 mt-7 block text-sm font-semibold text-slate-700">Tên học viên</label>
          <input
            id="speaking-name"
            type="text"
            value={studentName}
            onChange={event => setStudentName(event.target.value)}
            placeholder="Ví dụ: Minh Anh"
            autoComplete="name"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3.5 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
            required
          />
          <button type="submit" className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 text-sm font-bold text-white shadow-lg shadow-slate-900/10 transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-blue-200">
            Vào khu vực luyện nói <ArrowRight size={17} aria-hidden="true" />
          </button>
          <p className="mt-4 text-center text-xs leading-5 text-slate-400">Chẩn đoán luyện tập không phải điểm IELTS chính thức.</p>
        </form>
      </div>
    );
  }

  const band = progress?.estimated_band;
  const streak = Number(progress?.streak ?? 0);

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,.75fr)]">
        <div className="relative isolate overflow-hidden rounded-[28px] bg-[#111b3d] px-6 py-8 text-white shadow-xl shadow-blue-950/10 sm:px-9 sm:py-10">
          <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-20 -z-10 h-72 w-72 rounded-full border-[36px] border-white/[0.035]" />
          <div aria-hidden="true" className="pointer-events-none absolute -bottom-28 right-32 -z-10 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl" />
          <div className="max-w-2xl">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.07] px-3 py-1.5 text-[11px] font-bold uppercase tracking-[.15em] text-blue-100">
              <Sparkles size={13} aria-hidden="true" /> Khu vực luyện nói
            </div>
            <h1 className="text-3xl font-extrabold leading-tight tracking-tight sm:text-[40px]">
              Chào {studentName},<br className="hidden sm:block" /> mình cùng luyện nói nhé.
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-blue-100/75 sm:text-base">
              Chọn một câu hỏi, ghi âm câu trả lời và xem rõ transcript, phản hồi cùng giới hạn của từng ước lượng.
            </p>
            <Link to="/speaking/practice" className="mt-7 inline-flex min-h-12 items-center gap-2 rounded-xl bg-white px-5 text-sm font-bold text-slate-950 shadow-lg transition hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/30">
              Chọn chủ đề luyện tập <ArrowRight size={17} aria-hidden="true" />
            </Link>
          </div>
        </div>

        <section aria-labelledby="progress-title" className="flex flex-col rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.14em] text-slate-400">Tiến độ cá nhân</p>
              <h2 id="progress-title" className="mt-1 text-lg font-bold text-slate-900">Nhịp luyện tập của bạn</h2>
            </div>
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-700"><ChartIcon /></span>
          </div>

          <div className="mt-6 rounded-2xl bg-slate-50 p-5">
            <div className="flex items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Band chẩn đoán</p>
                <p className="mt-1 text-4xl font-extrabold tracking-tight text-slate-950">
                  {loading ? <span className="inline-block h-10 w-16 animate-pulse rounded-lg bg-slate-200" /> : band == null ? '—' : Number(band).toFixed(1)}
                </p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-[11px] font-semibold text-slate-500 ring-1 ring-slate-200">Chỉ khi đủ căn cứ</span>
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between rounded-2xl border border-orange-100 bg-orange-50/70 p-4">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white text-orange-500 shadow-sm"><Flame size={19} aria-hidden="true" /></span>
              <div><p className="text-xs font-semibold text-orange-800">Chuỗi ngày luyện</p><p className="text-xs text-orange-700/70">Duy trì nhịp học của bạn</p></div>
            </div>
            <p className="text-2xl font-extrabold text-orange-700">{loading ? '—' : streak}<span className="ml-1 text-xs font-semibold">ngày</span></p>
          </div>

          <Link to="/speaking/history" className="mt-auto inline-flex min-h-11 items-center justify-between gap-2 pt-5 text-sm font-bold text-blue-700 hover:text-blue-900">
            Xem lịch sử và tiến độ <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </section>
      </section>

      <section aria-labelledby="practice-options">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.15em] text-blue-700">Chọn cách luyện</p>
            <h2 id="practice-options" className="mt-1 text-2xl font-extrabold tracking-tight text-slate-950">Bạn muốn bắt đầu thế nào?</h2>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Link to="/speaking/practice" className="group flex min-h-44 items-center gap-5 rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg hover:shadow-blue-900/[0.05] sm:p-7">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-blue-50 text-blue-700 transition group-hover:bg-blue-600 group-hover:text-white"><BookOpen size={24} aria-hidden="true" /></span>
            <span className="min-w-0 flex-1">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wider text-blue-700">Practice</span>
              <span className="block text-xl font-bold text-slate-950">Luyện theo chủ đề</span>
              <span className="mt-1 block text-sm leading-5 text-slate-500">Chọn Part, chọn câu hỏi và luyện từng câu theo nhịp của bạn.</span>
            </span>
            <ArrowRight className="shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-blue-600" size={20} aria-hidden="true" />
          </Link>

          <Link to="/speaking/mock-test" className="group flex min-h-44 items-center gap-5 rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-violet-200 hover:shadow-lg hover:shadow-violet-900/[0.05] sm:p-7">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-violet-50 text-violet-700 transition group-hover:bg-violet-600 group-hover:text-white"><Play size={23} aria-hidden="true" /></span>
            <span className="min-w-0 flex-1">
              <span className="mb-1 block text-xs font-bold uppercase tracking-wider text-violet-700">Mock test</span>
              <span className="block text-xl font-bold text-slate-950">Làm bài thi thử</span>
              <span className="mt-1 block text-sm leading-5 text-slate-500">Đi lần lượt qua ba phần; mỗi câu trả lời được lưu trong phiên.</span>
            </span>
            <ArrowRight className="shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-violet-600" size={20} aria-hidden="true" />
          </Link>
        </div>
      </section>

      <div className="flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50/70 px-4 py-3.5 text-sm leading-6 text-blue-900/80">
        <Clock3 className="mt-0.5 shrink-0 text-blue-700" size={17} aria-hidden="true" />
        <p>Ở Part 2, bạn có một phút chuẩn bị. Trong các phần còn lại, hãy trả lời tự nhiên và nghe lại bản ghi trước khi nộp.</p>
      </div>
    </div>
  );
}

function ChartIcon() {
  return <History size={19} aria-hidden="true" />;
}
