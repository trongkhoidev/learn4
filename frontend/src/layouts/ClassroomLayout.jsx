import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { listClasses, getClass } from "../features/classes/api.js";
import { 
  LayoutDashboard, BookOpen, LogOut, ClipboardList, History, 
  Menu, X, Link as LinkIcon, Mic
} from "lucide-react";

export default function ClassroomLayout({ role }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const isTeacher = role === "teacher";
  const isStudent = role === "student";
  
  const matchStudent = location.pathname.match(/^\/student\/([^/]+)/);
  const studentClassId = matchStudent ? matchStudent[1] : null;

  const [classes, setClasses] = useState([]);
  const [studentClass, setStudentClass] = useState(null);

  useEffect(() => {
    if (isTeacher) {
      if (localStorage.getItem("teacher_code")) {
        listClasses().then(setClasses).catch(() => {});
      }
    }
  }, [isTeacher, location.pathname]);

  useEffect(() => {
    if (isStudent && studentClassId) {
      getClass(studentClassId).then(setStudentClass).catch(() => {});
    }
  }, [isStudent, studentClassId]);

  const matchTeacherClass = location.pathname.match(/^\/teacher\/class\/([^/]+)/);
  const teacherClassId = matchTeacherClass ? matchTeacherClass[1] : null;

  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  const toggleSidebar = () => setIsMobileOpen(!isMobileOpen);

  if (isTeacher) {
    return (
      <div className="teacher-shell flex min-h-[100dvh] w-full bg-[#f7f7f2] text-[#29332f] font-sans">
        {isMobileOpen && <button aria-label="Đóng menu" className="fixed inset-0 z-40 bg-[#10251e]/50 md:hidden" onClick={toggleSidebar} />}
        <aside className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#19352c] text-[#dbe5dc] transition-transform duration-200 md:sticky md:top-0 md:h-[100dvh] md:translate-x-0 ${isMobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-5">
            <Link to="/teacher" className="flex items-center gap-3 text-lg font-semibold tracking-tight text-white"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#769b83] text-lg">L</span>LexiLearn</Link>
            <button className="rounded-lg p-2 text-[#b8c5bb] hover:bg-white/5 md:hidden" onClick={toggleSidebar}><X size={19} /></button>
          </div>
          <nav className="flex-1 overflow-y-auto py-4">
            <Link to="/teacher" className={`mx-3 flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm transition ${location.pathname === "/teacher" ? "bg-white/10 text-white" : "text-[#c5d0c7] hover:bg-white/5 hover:text-white"}`}><LayoutDashboard size={18} />Tổng quan</Link>
            <p className="mb-2 mt-7 px-6 text-[10px] font-semibold uppercase tracking-[.14em] text-[#9eafa3]">Trung tâm</p>
            <Link to="/teacher" className="mx-3 flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm text-[#c5d0c7] transition hover:bg-white/5 hover:text-white"><BookOpen size={18} />Cấp độ & lớp học</Link>
            <Link to="/teacher" className="mx-3 flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm text-[#c5d0c7] transition hover:bg-white/5 hover:text-white"><ClipboardList size={18} />Bài tập & chấm điểm</Link>
            <Link to="/speaking" className="mx-3 flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm text-[#c5d0c7] transition hover:bg-white/5 hover:text-white"><Mic size={18} />Speaking AI</Link>
            <p className="mb-2 mt-7 px-6 text-[10px] font-semibold uppercase tracking-[.14em] text-[#9eafa3]">Lớp đang hoạt động</p>
            <div className="space-y-1">{classes.map((cls) => <Link key={cls.id} to={`/teacher/class/${cls.id}`} className={`mx-3 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${teacherClassId === cls.id ? "bg-white/10 text-white" : "text-[#c5d0c7] hover:bg-white/5 hover:text-white"}`}><BookOpen size={17} /><span className="min-w-0"><span className="block truncate">{cls.name}</span><span className="block truncate text-[10px] text-[#9eafa3]">{cls.level || "General English B1"}</span></span></Link>)}</div>
          </nav>
          <div className="border-t border-white/10 p-4"><button onClick={() => { localStorage.removeItem("teacher_code"); navigate("/teacher"); window.location.reload(); }} className="flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-sm text-[#c5d0c7] transition hover:bg-white/5 hover:text-white"><LogOut size={18} />Đăng xuất</button></div>
        </aside>
        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-[#e4e8e2] bg-[#f7f7f2]/95 px-4 backdrop-blur md:hidden">
            <button aria-label="Mở menu" onClick={toggleSidebar} className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-[#19352c] hover:bg-[#eaf1eb]"><Menu size={21} /></button>
            <span className="text-sm font-semibold text-[#19352c]">LexiLearn · Quản lý</span>
            <span className="w-11" />
          </header>
          <main className="min-h-[100dvh] px-4 py-6 md:px-8 md:py-9 xl:px-10"><Outlet /></main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-slate-50 text-slate-800 font-sans overflow-hidden">
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 md:hidden"
          onClick={toggleSidebar}
        />
      )}

      <aside className={`fixed md:static inset-y-0 left-0 w-64 bg-slate-900 text-slate-300 flex flex-col shadow-xl z-50 transform transition-transform duration-200 ease-in-out ${isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <>
          <div className="p-5 bg-slate-950 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-emerald-600 rounded flex items-center justify-center text-white font-bold text-xl">
                {studentClass?.name?.charAt(0) || "C"}
              </div>
              <div className="overflow-hidden">
                <div className="text-sm font-bold text-white tracking-wide truncate">{studentClass?.name || "Đang tải..."}</div>
                <div className="text-xs text-slate-500 truncate">Mã: {studentClass?.share_code || "---"}</div>
              </div>
            </div>
            <button className="md:hidden text-slate-400" onClick={toggleSidebar}><X size={24} /></button>
          </div>
          <nav className="flex-1 py-4">
            <Link
              to={`/student/${studentClassId}`}
              className={`flex items-center gap-3 px-6 py-3 transition-colors ${location.pathname === `/student/${studentClassId}` ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white text-slate-400'}`}
            >
              <ClipboardList size={20} />
              <span>Bài tập</span>
            </Link>
            <a
              href="#history"
              className="flex items-center gap-3 px-6 py-3 transition-colors hover:bg-slate-800 hover:text-white text-slate-400"
              onClick={(event) => {
                if (location.pathname !== `/student/${studentClassId}`) {
                  event.preventDefault();
                  navigate(`/student/${studentClassId}#history`);
                } else {
                  const element = document.getElementById("history");
                  if (element) element.scrollIntoView({ behavior: "smooth" });
                }
                setIsMobileOpen(false);
              }}
            >
              <History size={20} />
              <span>Lịch sử</span>
            </a>
            <div className="my-4 border-t border-slate-800" />
            <Link to="/join" className="flex items-center gap-3 px-6 py-3 transition-colors hover:bg-slate-800 hover:text-white text-slate-400">
              <LinkIcon size={20} />
              <span>Vào lớp khác</span>
            </Link>
            <Link to="/speaking" className="flex items-center gap-3 px-6 py-3 transition-colors hover:bg-slate-800 hover:text-white text-slate-400">
              <Mic size={20} />
              <span>Luyện Nói (IELTS)</span>
            </Link>
          </nav>
          <div className="p-4 bg-slate-950 flex items-center gap-3 text-slate-300">
            <div className="w-8 h-8 bg-slate-800 rounded-full flex items-center justify-center text-sm font-medium">
              {(localStorage.getItem(`student_name_${studentClassId}`) || "S")[0].toUpperCase()}
            </div>
            <div className="truncate text-sm font-medium">
              {localStorage.getItem(`student_name_${studentClassId}`) || "Học viên"}
            </div>
          </div>
        </>
      </aside>

      <div className="flex-1 flex flex-col h-screen min-w-0">
        <header className="md:hidden flex items-center h-16 bg-white border-b px-4 shrink-0">
          <button onClick={toggleSidebar} className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg">
            <Menu size={24} />
          </button>
          <span className="ml-3 font-semibold text-slate-800">
            {studentClass?.name || "LexiLearn"}
          </span>
        </header>
        <main className="flex-1 overflow-y-auto relative bg-slate-50">
          <div className="w-full mx-auto p-4 md:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
