import * as classApi from "../api.js";
import * as assignmentApi from "../../assignments/api.js";
import * as submissionApi from "../../submissions/api.js";
import { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "../../../shared/ui/Card";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { Spinner } from "../../../shared/ui/Spinner";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { ClipboardList, History, CheckCircle2 } from "lucide-react";
import { SKILLS, getDeadlineStatus } from "../../assignments/model/constants.js";

export default function StudentHome() {
  const { classId } = useParams();
  const navigate = useNavigate();
  const [cls, setCls] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const name = localStorage.getItem(`student_name_${classId}`) || "";

  useEffect(() => {
    if (!name) {
      navigate(`/join`); // Need name to join, go to join page without pre-filling wrong code
      return;
    }
    
    Promise.all([
      classApi.getClass(classId).catch(() => null),
      assignmentApi.listAssignments(classId).catch(() => []),
      submissionApi.roster(classId, name).catch(() => [])
    ]).then(([c, a, h]) => {
      setCls(c);
      setAssignments(a);
      setHistory(h);
      setLoading(false);
    });
  }, [classId, name, navigate]);

  // Create a map of assignment_id -> latest submission
  const submissionMap = useMemo(() => {
    const map = {};
    history.forEach(sub => {
      if (!map[sub.assignment_id]) {
        map[sub.assignment_id] = sub;
      }
    });
    return map;
  }, [history]);

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-8 rounded-2xl shadow-lg text-white relative overflow-hidden">
        <div className="absolute top-0 right-0 p-12 opacity-10 pointer-events-none">
          <GraduationCapBg className="w-64 h-64" />
        </div>
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Xin chào, {name}! 👋</h1>
          <p className="text-blue-100 text-lg">{cls?.name ? `Lớp ${cls.name}` : "Chào mừng trở lại"}</p>
        </div>
      </div>

      <div className="space-y-6">
        <div className="flex items-center gap-2 mb-4">
          <ClipboardList className="text-blue-600" size={24} />
          <h2 className="text-xl font-bold text-slate-800">Bài tập của bạn</h2>
        </div>
        
        {assignments.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {assignments.map((a) => {
              const sType = SKILLS[a.skill] || { label: a.skill, color: "bg-slate-100", icon: ClipboardList };
              const Icon = sType.icon;
              const status = getDeadlineStatus(a.deadline);
              const sub = submissionMap[a.id];
              const isDone = !!sub;
              
              return (
                <Card key={a.id} className="p-5 flex flex-col hover:shadow-lg transition-all duration-300 border border-slate-200/60 group">
                  <div className="flex justify-between items-start mb-3">
                    <div className={`px-2.5 py-1 rounded-md border text-xs font-semibold flex items-center gap-1.5 w-fit ${sType.color}`}>
                      <Icon size={12} /> {sType.label}
                    </div>
                    {status && (
                      <span className={`text-xs px-2 py-1 rounded border font-medium ${status.color}`}>
                        {status.text}
                      </span>
                    )}
                  </div>
                  
                  <h3 className="font-bold text-slate-800 text-lg mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
                    {a.title}
                  </h3>
                  
                  <div className="flex-1 mt-auto pt-4 flex items-center justify-between">
                    {isDone ? (
                      <div className="flex items-center gap-1.5 text-sm font-medium text-emerald-600">
                        <CheckCircle2 size={16} />
                        {sub.score !== null ? `${sub.score.toFixed(1)} điểm` : "Đã nộp"}
                      </div>
                    ) : (
                      <div className="text-sm font-medium text-slate-400">
                        Chưa làm
                      </div>
                    )}
                    
                    <Button 
                      variant={isDone ? "outline" : "primary"} 
                      size="sm" 
                      onClick={() => navigate(`/student/${classId}/assignment/${a.id}`)}
                      className={isDone ? "" : "shadow-md"}
                    >
                      {isDone ? "Xem lại" : "Làm bài"}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        ) : (
          <EmptyState
            icon={ClipboardList}
            title="Tuyệt vời!"
            description="Chưa có bài tập nào mới. Hãy nghỉ ngơi và quay lại sau nhé!"
          />
        )}
      </div>
      
      <div id="history" className="pt-8 scroll-mt-20">
        <div className="flex items-center gap-2 mb-6 border-b border-slate-200 pb-2">
          <History className="text-slate-600" size={24} />
          <h2 className="text-xl font-bold text-slate-800">Lịch sử làm bài</h2>
        </div>
        
        {history.length > 0 ? (
          <Card className="overflow-hidden border border-slate-200 shadow-sm">
            <ul className="divide-y divide-slate-100">
              {history.map((h) => (
                <li key={h.id} className="flex flex-col sm:flex-row sm:items-center justify-between p-5 hover:bg-slate-50 transition-colors gap-4">
                  <div>
                    <h4 className="font-bold text-slate-800 text-lg mb-1">{h.assignment_title || "Bài tập"}</h4>
                    <p className="text-sm text-slate-500">Nộp lúc: {new Date(h.submitted_at).toLocaleString('vi-VN')}</p>
                  </div>
                  
                  <div className="flex items-center gap-4 self-start sm:self-auto">
                    <div className="flex flex-col items-end">
                      <span className="font-bold text-lg text-slate-800">{h.score !== null ? h.score.toFixed(1) : "-"}</span>
                      <Badge variant={h.status === "graded" ? "success" : "warning"} className="mt-1">
                        {h.status === "graded" ? "Đã chấm" : "Chờ chấm"}
                      </Badge>
                    </div>
                    
                    <Button 
                      variant="outline" 
                      onClick={() => navigate(`/student/${classId}/assignment/${h.assignment_id}`)}
                      className="shrink-0"
                    >
                      Xem lại
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        ) : (
          <div className="text-center py-12 text-slate-500 bg-white rounded-xl border border-dashed border-slate-200">
            Bạn chưa nộp bài tập nào.
          </div>
        )}
      </div>
    </div>
  );
}

function GraduationCapBg(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M21.42 10.922a2 2 0 0 1-.01 2.833l-7.1 7.1a2 2 0 0 1-2.82.01l-7.11-7.1a2 2 0 0 1-.01-2.833l7.1-7.1a2 2 0 0 1 2.82-.01l7.11 7.1Z"/>
      <path d="M12 15V3"/>
      <path d="M16 11v4"/>
    </svg>
  );
}
