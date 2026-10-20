import * as classApi from "../api.js";
import * as assignmentApi from "../../assignments/api.js";
import * as submissionApi from "../../submissions/api.js";
import { useCallback, useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "../../../shared/ui/Card";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../../shared/ui/Tabs";
import { Modal } from "../../../shared/ui/Modal";
import { ConfirmDialog } from "../../../shared/ui/ConfirmDialog";
import { useToast } from "../../../shared/ui/Toast";
import { Spinner } from "../../../shared/ui/Spinner";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { Copy, Edit, Trash2, Plus, ClipboardList } from "lucide-react";
import FeedbackPanel from "../../submissions/components/FeedbackPanel.jsx";
import ReasoningCards from "../../submissions/components/ReasoningCards.jsx";
import WritingResult from "../../writing/components/WritingResult.jsx";
import { SKILLS, getDeadlineStatus } from "../../assignments/model/constants.js";

export default function ClassDetail() {
  const { classId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [cls, setCls] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [submissionsMap, setSubmissionsMap] = useState({}); // asm_id -> submissions array
  const [loading, setLoading] = useState(true);
  
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [assignmentToDelete, setAssignmentToDelete] = useState(null);

  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [isSubmissionModalOpen, setIsSubmissionModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const clsData = await classApi.getClass(classId);
      setCls(clsData);
      
      const asms = await assignmentApi.listAssignments(classId);
      setAssignments(asms);
      
      const subMap = {};
      await Promise.all(
        asms.map(async (a) => {
          subMap[a.id] = await submissionApi.listSubmissions(a.id);
        })
      );
      setSubmissionsMap(subMap);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [classId, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const joinUrl = cls ? `${window.location.origin}/join?code=${cls.share_code}` : "";

  function copyCode() {
    navigator.clipboard.writeText(joinUrl);
    toast.info("Đã copy link mời!");
  }

  async function handleDeleteAssignment() {
    if (!assignmentToDelete) return;
    try {
      await assignmentApi.deleteAssignment(assignmentToDelete.id);
      toast.success("Đã xóa bài tập!");
      setIsDeleteOpen(false);
      setAssignmentToDelete(null);
      loadData();
    } catch (e) {
      toast.error(e.message);
    }
  }

  // Calculate student grades matrix
  const studentMatrix = useMemo(() => {
    const students = {};
    Object.values(submissionsMap).flat().forEach(sub => {
      if (!students[sub.student_name]) {
        students[sub.student_name] = { name: sub.student_name, totalScore: 0, count: 0, submissions: {} };
      }
      students[sub.student_name].submissions[sub.assignment_id] = sub;
      if (sub.score != null) {
        students[sub.student_name].totalScore += sub.score;
        students[sub.student_name].count += 1;
      }
    });
    
    return Object.values(students)
      .map(s => ({ ...s, avgScore: s.count > 0 ? s.totalScore / s.count : 0 }))
      .sort((a, b) => b.avgScore - a.avgScore);
  }, [submissionsMap]);

  if (loading && !cls) {
    return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">{cls?.name}</h1>
              <Badge variant="emerald">{cls?.level || "General English B1"}</Badge>
            </div>
            <p className="text-slate-500 mt-1">{cls?.teacher_note || "Không có ghi chú"}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" onClick={copyCode} className="gap-2">
              <Copy size={16} /> Link mời
            </Button>
            {/* Note: Update and Delete class buttons can be handled from Dashboard or added here */}
          </div>
        </div>
      </div>

      <Tabs defaultValue="assignments">
        <TabsList>
          <TabsTrigger value="assignments">Bài tập</TabsTrigger>
          <TabsTrigger value="students">Học viên & Điểm</TabsTrigger>
        </TabsList>

        <TabsContent value="assignments" className="space-y-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-800">Danh sách bài tập ({assignments.length})</h2>
            <Button onClick={() => navigate(`/teacher/class/${classId}/new`)} className="gap-2">
              <Plus size={16} /> Bài tập mới
            </Button>
          </div>

          {assignments.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {assignments.map(a => {
                const sType = SKILLS[a.skill] || { label: a.skill, color: "bg-slate-100", icon: ClipboardList };
                const Icon = sType.icon;
                const status = getDeadlineStatus(a.deadline);
                const subCount = submissionsMap[a.id]?.length || 0;
                
                return (
                  <Card key={a.id} className="p-5 flex flex-col hover:shadow-md transition-shadow">
                    <div className="flex justify-between items-start mb-3">
                      <div className={`px-2.5 py-1 rounded-md border text-xs font-semibold flex items-center gap-1.5 w-fit ${sType.color}`}>
                        <Icon size={12} /> {sType.label}
                      </div>
                      <div className="flex gap-1">
                        <button onClick={() => navigate(`/teacher/class/${classId}/edit/${a.id}`)} className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded">
                          <Edit size={16} />
                        </button>
                        <button onClick={() => {
                          setAssignmentToDelete(a);
                          setIsDeleteOpen(true);
                        }} className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                    
                    <h3 className="font-bold text-slate-800 text-lg mb-2 line-clamp-1">{a.title}</h3>
                    
                    <div className="flex-1 space-y-2 mb-4">
                      {a.question_count > 0 && <p className="text-sm text-slate-500">• {a.question_count} câu hỏi</p>}
                      {status && <span className={`text-xs px-2 py-0.5 rounded border font-medium ${status.color}`}>{status.text}</span>}
                    </div>
                    
                    <div className="pt-3 border-t border-slate-100 flex justify-between items-center">
                      <span className="text-sm font-medium text-slate-500">{subCount} bài nộp</span>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={ClipboardList}
              title="Chưa có bài tập"
              description="Lớp này chưa có bài tập nào. Hãy tạo bài tập đầu tiên!"
              action={<Button onClick={() => navigate(`/teacher/class/${classId}/new`)}>+ Bài tập mới</Button>}
            />
          )}
        </TabsContent>

        <TabsContent value="students" className="space-y-4">
          <Card className="overflow-hidden border border-slate-200 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-4 font-semibold text-slate-700">Học viên</th>
                    <th className="px-6 py-4 font-semibold text-slate-700 text-center">Điểm TB</th>
                    {assignments.map(a => (
                      <th key={a.id} className="px-6 py-4 font-semibold text-slate-700 text-center max-w-[150px] truncate" title={a.title}>
                        {a.title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {studentMatrix.length > 0 ? (
                    studentMatrix.map((student, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-6 py-4 font-medium text-slate-800 flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                            {student.name.charAt(0).toUpperCase()}
                          </div>
                          {student.name}
                        </td>
                        <td className="px-6 py-4 text-center font-bold text-slate-700">
                          {student.avgScore > 0 ? student.avgScore.toFixed(1) : "-"}
                        </td>
                        {assignments.map(a => {
                          const sub = student.submissions[a.id];
                          return (
                            <td key={a.id} className="px-6 py-4 text-center">
                              {sub ? (
                                <button
                                  onClick={() => {
                                    setSelectedSubmission(sub);
                                    setIsSubmissionModalOpen(true);
                                  }}
                                  className={`px-3 py-1 rounded-full text-xs font-semibold ${sub.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700 hover:bg-green-200'} transition-colors`}
                                >
                                  {sub.score !== null ? sub.score.toFixed(1) : (sub.status === 'pending' ? 'Đang chấm' : 'Chấm tay')}
                                </button>
                              ) : (
                                <span className="text-slate-300">-</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={assignments.length + 2} className="px-6 py-12 text-center text-slate-500">
                        Chưa có dữ liệu học viên.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        title="Xóa bài tập"
        message={`Bạn có chắc muốn xóa bài tập "${assignmentToDelete?.title}"? Mọi bài nộp sẽ bị xóa.`}
        confirmLabel="Xóa"
        danger={true}
        onConfirm={handleDeleteAssignment}
      />

      <Modal
        open={isSubmissionModalOpen}
        onClose={() => setIsSubmissionModalOpen(false)}
        title={`Bài nộp của ${selectedSubmission?.student_name}`}
        size="lg"
      >
        {selectedSubmission && (
          <SubmissionDetail 
            submission={selectedSubmission} 
            onUpdate={() => {
              loadData(); // reload all data to update grades
            }} 
          />
        )}
      </Modal>
    </div>
  );
}

function SubmissionDetail({ submission, onUpdate }) {
  const [score, setScore] = useState(submission.score ?? "");
  const { toast } = useToast();

  async function save() {
    try {
      await submissionApi.patchSubmission(submission.id, { score: score === "" ? null : Number(score) });
      toast.success("Đã cập nhật điểm!");
      onUpdate && onUpdate();
    } catch (e) {
      toast.error("Lỗi: " + e.message);
    }
  }

  const result = submission.result;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
        <div>
          <p className="text-sm font-medium text-slate-500">Điểm hiện tại</p>
          <div className="flex items-center gap-3 mt-1">
            <input 
              type="number" 
              className="w-24 rounded-lg border-slate-300 shadow-sm p-2 text-lg font-bold" 
              value={score} 
              onChange={(e) => setScore(e.target.value)} 
              placeholder="---" 
            />
            <Button onClick={save} variant="primary">Lưu điểm</Button>
          </div>
        </div>
        <div className="ml-auto text-right">
          <p className="text-sm font-medium text-slate-500">Trạng thái</p>
          <Badge variant={submission.status === 'graded' ? 'success' : 'warning'} className="mt-1">
            {submission.status === 'graded' ? 'Đã chấm' : 'Đang xử lý'}
          </Badge>
        </div>
      </div>

      {submission.audio_url && (
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
          <p className="text-sm font-medium text-slate-700 mb-2">File Ghi âm</p>
          <audio controls src={submission.audio_url} className="w-full h-10" />
        </div>
      )}

      <div className="pt-4 border-t border-slate-100">
        <h3 className="font-semibold text-slate-800 mb-4">Chi tiết đánh giá</h3>
        {result?.error ? (
          <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
            Lỗi phân tích: {result.error}
          </div>
        ) : result?.task_response || result?.grammatical_accuracy ? (
          <WritingResult result={result} />
        ) : result?.overall !== undefined || result?.pronun ? (
          <div className="space-y-6">
            <FeedbackPanel result={result} />
            {result.grammar?.errors && <ReasoningCards errors={result.grammar.errors} />}
          </div>
        ) : submission.answers ? (
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="font-medium mb-2">Đáp án học sinh nộp:</p>
            <div className="flex flex-wrap gap-2">
              {submission.answers.map((ans, i) => (
                <div key={i} className="px-3 py-1 bg-white border rounded shadow-sm text-sm">
                  <span className="text-slate-400 mr-2">{i+1}.</span>
                  <span className="font-medium">{ans || "(Trống)"}</span>
                </div>
              ))}
            </div>
            {result?.results && (
              <div className="mt-4">
                <p className="font-medium mb-2">Đánh giá:</p>
                <div className="flex flex-wrap gap-2">
                  {result.results.map((r, i) => (
                    <div key={i} className={`px-3 py-1 border rounded shadow-sm text-sm ${r.correct ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                      {i+1}. {r.correct ? 'Đúng' : 'Sai'}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 border border-dashed rounded-xl">
            Hệ thống chưa trả kết quả chi tiết.
          </div>
        )}
      </div>
    </div>
  );
}
