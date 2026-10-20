import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 p-4 relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
      <div className="absolute top-[20%] right-[-10%] w-96 h-96 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
      <div className="absolute bottom-[-20%] left-[20%] w-96 h-96 bg-pink-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>

      <div className="relative z-10 text-center max-w-2xl bg-white/80 backdrop-blur-xl p-12 rounded-3xl shadow-2xl border border-white/50">
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 bg-blue-600 rounded-2xl flex items-center justify-center text-white font-bold text-4xl shadow-lg transform rotate-3">L</div>
        </div>
        <h1 className="text-5xl font-extrabold text-slate-800 tracking-tight mb-4">LexiLearn</h1>
        <p className="text-lg text-slate-600 mb-10 max-w-md mx-auto leading-relaxed">
          Nền tảng luyện thi 4 kỹ năng tiếng Anh toàn diện dành cho giáo viên và học viên.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link 
            to="/speaking" 
            className="group relative flex h-14 items-center justify-center gap-2 rounded-xl bg-blue-600 px-8 text-white font-semibold shadow-lg hover:bg-blue-700 hover:shadow-xl hover:-translate-y-0.5 transition-all w-full sm:w-auto"
          >
            <span>🎙️</span>
            <span>Trải nghiệm IELTS Speaking AI</span>
          </Link>
          <Link 
            to="/teacher" 
            className="group relative flex h-14 items-center justify-center gap-2 rounded-xl bg-white px-8 text-blue-600 font-semibold shadow-md border border-blue-100 hover:border-blue-300 hover:shadow-lg hover:-translate-y-0.5 transition-all w-full sm:w-auto"
          >
            <span>👨‍🏫</span>
            <span>Dành cho Giáo viên</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
