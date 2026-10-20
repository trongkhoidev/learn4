import * as speakingApi from '../api.js';
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Award, ChartNoAxesCombined,
  CircleHelp, Flame, History, Mic2,
} from 'lucide-react';
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const statusLabels = {
  scored: 'Đủ bằng chứng',
  partial: 'Một phần',
  cant_hear: 'Chưa nghe rõ',
  insufficient_sample: 'Mẫu quá ngắn',
  needs_review: 'Cần nghe lại',
  failed: 'Không chấm được',
  pending: 'Đang chờ',
  processing: 'Đang xử lý',
};

function StatusBadge({ status }) {
  const tone = status === 'scored'
    ? 'bg-emerald-50 text-emerald-800'
    : ['pending', 'processing'].includes(status)
      ? 'bg-blue-50 text-blue-800'
      : status === 'failed' || status === 'needs_review'
        ? 'bg-amber-50 text-amber-900'
        : 'bg-slate-100 text-slate-700';

  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold ${tone}`}>{statusLabels[status] || status || 'Chưa rõ trạng thái'}</span>;
}

export default function SpeakingHistory() {
  const [history, setHistory] = useState([]);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const studentName = localStorage.getItem('speaking_name') || 'Guest';

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      setLoading(true);
      try {
        const [items, currentProgress] = await Promise.all([
          speakingApi.getSpeakingHistory(studentName),
          speakingApi.getSpeakingProgress(studentName),
        ]);
        if (!cancelled) {
          setHistory(items || []);
          setProgress(currentProgress || { estimated_band: null, streak: 0 });
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setHistory([]);
          setProgress({ estimated_band: null, streak: 0 });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, [studentName]);

  const chartData = [...history]
    .filter(item => item.score != null)
    .reverse()
    .map(item => ({
      date: new Date(item.created_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'numeric' }),
      score: Number(item.score),
    }));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link to="/speaking" className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-slate-500 transition hover:text-blue-700"><ArrowLeft size={16} /> Quay lại Dashboard</Link>

      <header className="flex flex-col justify-between gap-4 rounded-[26px] bg-gradient-to-br from-[#111b3d] via-[#1c2d61] to-[#3642a0] p-6 text-white shadow-lg shadow-blue-950/10 sm:flex-row sm:items-end sm:p-8">
        <div>
          <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[.16em] text-blue-200"><History size={14} /> Nhật ký luyện tập</p>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Lịch sử &amp; Tiến độ</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-blue-100/75">Xem lại các phiên, trạng thái đánh giá và band có đủ bằng chứng.</p>
        </div>
        <Link to="/speaking/practice" className="inline-flex min-h-11 w-fit items-center gap-2 rounded-xl bg-white px-4 text-sm font-bold text-slate-950 transition hover:bg-blue-50">Luyện một câu mới <ArrowRight size={16} /></Link>
      </header>

      <section aria-label="Tóm tắt tiến độ" className="grid gap-3 sm:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-wider text-slate-500">Band chẩn đoán</p><span className="grid h-9 w-9 place-items-center rounded-xl bg-blue-50 text-blue-700"><Award size={18} /></span></div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-slate-950">{loading ? '—' : progress?.estimated_band == null ? '—' : Number(progress.estimated_band).toFixed(1)}</p>
          <p className="mt-1 flex items-start gap-1.5 text-xs leading-5 text-slate-500"><CircleHelp size={13} className="mt-0.5 shrink-0" /> Chỉ tổng hợp phiên có overall hợp lệ.</p>
        </article>
        <article className="rounded-2xl border border-orange-100 bg-orange-50/70 p-5">
          <div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-wider text-orange-800">Chuỗi ngày</p><span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-orange-600"><Flame size={18} /></span></div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-orange-900">{loading ? '—' : Number(progress?.streak ?? 0)} <span className="text-sm font-bold">ngày</span></p>
          <p className="mt-1 text-xs leading-5 text-orange-900/60">Nhịp học liên tục của bạn.</p>
        </article>
        <article className="rounded-2xl border border-violet-100 bg-violet-50/70 p-5">
          <div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-wider text-violet-800">Tổng phiên</p><span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-violet-700"><ChartNoAxesCombined size={18} /></span></div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-violet-950">{loading ? '—' : history.length}</p>
          <p className="mt-1 text-xs leading-5 text-violet-900/60">Bao gồm cả phiên chưa có band.</p>
        </article>
      </section>

      {loading ? (
        <section role="status" className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-sm">
          <div className="h-5 w-44 animate-pulse rounded bg-slate-100" />
          <div className="mt-5 space-y-3"><div className="h-16 animate-pulse rounded-2xl bg-slate-50" /><div className="h-16 animate-pulse rounded-2xl bg-slate-50" /></div>
        </section>
      ) : (
        <>
          {chartData.length > 0 && (
            <section aria-labelledby="band-trend-title" className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
              <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
                <div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-blue-700">Tiến độ</p><h2 id="band-trend-title" className="mt-1 text-lg font-bold text-slate-950">Band tổng thể theo phiên</h2></div>
                <p className="text-xs text-slate-500">Chỉ hiện phiên có đủ dữ liệu để tính overall.</p>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 12, right: 12, bottom: 4, left: -18 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9edf5" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                    <YAxis domain={[0, 9]} ticks={[0, 3, 6, 9]} axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip contentStyle={{ borderRadius: 14, border: '1px solid #e2e8f0', boxShadow: '0 8px 30px #0f172a12' }} />
                    <Line type="monotone" dataKey="score" name="Band" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4, fill: '#4f46e5', stroke: '#fff', strokeWidth: 2 }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}

          <section aria-labelledby="history-list-title" className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-col justify-between gap-3 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:px-7">
              <div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-slate-400">Các phiên gần đây</p><h2 id="history-list-title" className="mt-1 text-lg font-bold text-slate-950">Bài luyện của {studentName}</h2></div>
              {history.length > 0 && <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{history.length} phiên</span>}
            </div>
            {history.length === 0 ? (
              <div className="px-5 py-12 text-center sm:px-7">
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-blue-700"><Mic2 size={22} /></span>
                <h3 className="mt-4 text-lg font-bold text-slate-950">Chưa có phiên luyện tập</h3>
                <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-slate-500">Bắt đầu bằng một câu hỏi. Bài luyện sẽ xuất hiện ở đây sau khi được gửi.</p>
                <Link to="/speaking/practice" className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white hover:bg-blue-700">Chọn chủ đề <ArrowRight size={16} /></Link>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {history.map((item, index) => {
                  const status = (item.result || {}).status || item.status;
                  return (
                    <article data-testid="speaking-history-row" key={item.id || index} className="flex flex-col gap-4 px-5 py-4 transition hover:bg-slate-50/70 sm:flex-row sm:items-center sm:justify-between sm:px-7">
                      <div className="flex min-w-0 items-center gap-3.5">
                        <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-2xl text-sm font-extrabold ${item.score == null ? 'bg-slate-100 text-slate-400' : 'bg-blue-50 text-blue-800'}`}>{item.score == null ? '—' : Number(item.score).toFixed(1)}</span>
                        <div className="min-w-0">
                          <h3 className="truncate text-sm font-bold text-slate-950">Phần thi: {item.part_type || 'PART 2'}</h3>
                          <p className="mt-1 text-xs text-slate-500">{new Date(item.created_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-3 sm:justify-end">
                        <StatusBadge status={status} />
                        <Link to={`/speaking/practice?session=${encodeURIComponent(item.id)}`} className="text-sm font-semibold text-blue-700 hover:text-blue-900">Xem phản hồi</Link>
                        {item.audio_url && <audio src={item.audio_url} controls preload="none" className="h-9 w-full max-w-56 sm:w-48" aria-label="Nghe lại bản ghi" />}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
