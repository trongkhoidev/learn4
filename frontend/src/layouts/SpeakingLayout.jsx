import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { BookOpen, ChartNoAxesCombined, ClipboardCheck, History, Mic2, Sparkles } from 'lucide-react';

const navigation = [
  { to: '/speaking', label: 'Tổng quan', icon: ChartNoAxesCombined },
  { to: '/speaking/practice', label: 'Luyện theo chủ đề', icon: BookOpen },
  { to: '/speaking/mock-test', label: 'Thi thử', icon: ClipboardCheck },
  { to: '/speaking/history', label: 'Lịch sử', icon: History },
];

function SpeakingNavigation({ pathname, compact = false }) {
  return (
    <nav
      aria-label="Điều hướng IELTS Speaking"
      className={compact ? 'flex gap-2 overflow-x-auto pb-3 lg:hidden' : 'hidden items-center gap-1 lg:flex'}
    >
      {navigation.map(({ to, label, icon: Icon }) => {
        const active = to === '/speaking'
          ? pathname === to
          : pathname === to || pathname.startsWith(`${to}/`);

        return (
          <Link
            key={to}
            to={to}
            aria-current={active ? 'page' : undefined}
            className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition-colors ${
              active
                ? 'bg-blue-50 text-blue-700'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Icon size={16} aria-hidden="true" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function SpeakingLayout() {
  const { pathname } = useLocation();
  const name = localStorage.getItem('speaking_name')?.trim();
  const initials = name ? name.slice(0, 1).toLocaleUpperCase('vi-VN') : 'L';

  return (
    <div className="min-h-screen bg-[#f4f6fb] text-slate-900">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-[68px] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:h-[76px] lg:px-8">
          <Link to="/speaking" className="flex shrink-0 items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 to-violet-600 text-white shadow-md shadow-blue-900/15">
              <Mic2 size={20} aria-hidden="true" />
            </span>
            <span className="leading-tight">
              <span className="block text-base font-extrabold tracking-tight text-slate-900">LexiLearn</span>
              <span className="block text-[10px] font-bold uppercase tracking-[.18em] text-slate-400">Speaking studio</span>
            </span>
          </Link>

          <SpeakingNavigation pathname={pathname} />

          <div className="flex min-w-0 items-center gap-2.5">
            <span className="hidden text-right sm:block">
              <span className="block max-w-32 truncate text-xs font-semibold text-slate-800">{name || 'Khu vực học viên'}</span>
              <span className="block text-[10px] text-slate-400">IELTS Speaking</span>
            </span>
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-blue-100 bg-blue-50 text-sm font-bold text-blue-700">
              {initials}
            </span>
          </div>
        </div>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SpeakingNavigation pathname={pathname} compact />
        </div>
      </header>

      <main className="mx-auto min-h-[calc(100dvh-140px)] max-w-7xl px-4 py-7 sm:px-6 sm:py-9 lg:px-8">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200/80 bg-white/70">
        <div className="mx-auto flex max-w-7xl items-start gap-2 px-4 py-4 text-xs leading-5 text-slate-500 sm:px-6 lg:px-8">
          <Sparkles size={14} className="mt-0.5 shrink-0 text-blue-500" aria-hidden="true" />
          <p>Phản hồi dùng để luyện tập. Band chỉ hiển thị khi tiêu chí có đủ bằng chứng và không thay thế kết quả IELTS chính thức.</p>
        </div>
      </footer>
    </div>
  );
}
