import * as assignmentApi from "../api.js";
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useToast } from "../../../shared/ui/Toast";
import { Card } from "../../../shared/ui/Card";
import { Button } from "../../../shared/ui/Button";
import { Input } from "../../../shared/ui/Input";
import { Textarea } from "../../../shared/ui/Textarea";
import { Select } from "../../../shared/ui/Select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../../shared/ui/Tabs";
import { ArrowLeft, Save, FileText, Headphones, Mic, PenTool, LayoutDashboard } from "lucide-react";
import { Spinner } from "../../../shared/ui/Spinner";

export default function AssignmentBuilder() {
  const { classId, assignmentId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const isEdit = !!assignmentId;
  
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  
  const [skill, setSkill] = useState("reading");
  
  // Common
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  
  // Reading/Listening
  const [questionCount, setQuestionCount] = useState(0);
  const [contentText, setContentText] = useState("");
  const [contentFile, setContentFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [answerKey, setAnswerKey] = useState([]); // array of strings
  
  // Speaking
  const [part1, setPart1] = useState("");
  const [part2, setPart2] = useState("");
  const [part3, setPart3] = useState("");
  const [isMock, setIsMock] = useState(false);
  
  // Writing
  const [writingTaskType, setWritingTaskType] = useState("task2");
  const [minWords, setMinWords] = useState(250);

  useEffect(() => {
    if (isEdit) {
      assignmentApi.getTeacherAssignment(assignmentId).then(data => {
        setSkill(data.skill);
        setTitle(data.title);
        if (data.deadline) {
          // parse datetime to local input format
          const d = new Date(data.deadline);
          d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
          setDeadline(d.toISOString().slice(0, 16));
        }
        
        setQuestionCount(data.question_count || 0);
        setContentText(data.content_text || "");
        if (data.answer_key) setAnswerKey(data.answer_key);
        
        if (data.speaking_parts) {
          setPart1(data.speaking_parts.part1 || "");
          setPart2(data.speaking_parts.part2 || "");
          setPart3(data.speaking_parts.part3 || "");
          setIsMock(data.speaking_parts.is_mock || false);
        }
        
        if (data.writing_task_type) setWritingTaskType(data.writing_task_type);
        if (data.min_words) setMinWords(data.min_words);
        else if (data.writing_task_type === 'task1') setMinWords(150);
        else setMinWords(250);
        
      }).catch(err => {
        toast.error("Không tải được dữ liệu: " + err.message);
      }).finally(() => {
        setLoading(false);
      });
    }
  }, [isEdit, assignmentId, toast]);

  // Adjust answer key array size when questionCount changes
  useEffect(() => {
    setAnswerKey(prev => {
      const newKeys = [...prev];
      if (newKeys.length > questionCount) return newKeys.slice(0, questionCount);
      while (newKeys.length < questionCount) newKeys.push("");
      return newKeys;
    });
  }, [questionCount]);

  function handleWritingTaskTypeChange(e) {
    const val = e.target.value;
    setWritingTaskType(val);
    setMinWords(val === "task1" ? 150 : 250);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim()) return toast.error("Vui lòng nhập tiêu đề bài tập");
    
    setSaving(true);
    const fd = new FormData();
    if (!isEdit) {
      fd.append("class_id", classId);
      fd.append("skill", skill);
    }
    
    fd.append("title", title);
    if (deadline) {
      fd.append("deadline", new Date(deadline).toISOString());
    } else {
      fd.append("deadline", "");
    }
    
    if (skill === "reading" || skill === "listening") {
      fd.append("question_count", String(questionCount));
      fd.append("content_text", contentText);
      fd.append("answer_key", JSON.stringify(answerKey));
      if (contentFile) fd.append("content_file", contentFile);
      if (skill === "listening" && audioFile) fd.append("audio_file", audioFile);
    }
    
    if (skill === "speaking") {
      fd.append("speaking_parts", JSON.stringify({ part1, part2, part3, is_mock: isMock }));
    }
    
    if (skill === "writing") {
      fd.append("writing_task_type", writingTaskType);
      fd.append("min_words", String(minWords));
      fd.append("content_text", contentText);
      if (contentFile) fd.append("content_file", contentFile);
    }

    try {
      if (isEdit) {
        await assignmentApi.updateAssignment(assignmentId, fd);
        toast.success("Cập nhật bài tập thành công!");
      } else {
        await assignmentApi.createAssignment(fd);
        toast.success("Tạo bài tập thành công!");
      }
      navigate(`/teacher/class/${classId}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto pb-20">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(`/teacher/class/${classId}`)} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
          <ArrowLeft size={24} className="text-slate-600" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{isEdit ? "Sửa bài tập" : "Tạo bài tập mới"}</h1>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Left Form */}
        <div className="flex-1 space-y-6">
          <Card className="p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-800 mb-2">Thông tin chung</h2>
            {!isEdit && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Kỹ năng</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'reading', label: 'Reading', icon: FileText, color: 'bg-blue-50 text-blue-700 border-blue-200' },
                    { id: 'listening', label: 'Listening', icon: Headphones, color: 'bg-amber-50 text-amber-700 border-amber-200' },
                    { id: 'speaking', label: 'Speaking', icon: Mic, color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
                    { id: 'writing', label: 'Writing', icon: PenTool, color: 'bg-purple-50 text-purple-700 border-purple-200' }
                  ].map(s => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setSkill(s.id)}
                      className={`flex flex-col items-center justify-center p-3 rounded-lg border-2 transition-all ${skill === s.id ? `${s.color} border-current shadow-sm` : 'border-slate-100 bg-white hover:bg-slate-50 text-slate-500'}`}
                    >
                      <s.icon size={24} className="mb-2" />
                      <span className="font-semibold text-sm">{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            <Input label="Tiêu đề bài tập" value={title} onChange={e => setTitle(e.target.value)} required placeholder="VD: Luyện thi IELTS Reading Test 1" />
            <Input label="Hạn nộp (Tùy chọn)" type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)} />
          </Card>

          <Card className="p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-800 mb-2">Nội dung đề</h2>
            
            {(skill === "reading" || skill === "listening") && (
              <>
                <Input label="Số câu hỏi" type="number" min="0" max="100" value={questionCount} onChange={e => setQuestionCount(Number(e.target.value))} />
                
                {skill === "listening" && (
                  <div className="space-y-1">
                    <label className="block text-sm font-medium text-slate-700">Audio (Mới)</label>
                    <input type="file" accept="audio/*" className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" onChange={e => setAudioFile(e.target.files[0])} />
                  </div>
                )}
                
                <Tabs defaultValue="text">
                  <TabsList>
                    <TabsTrigger value="text">Dán Text</TabsTrigger>
                    <TabsTrigger value="file">Upload File (Ảnh/PDF)</TabsTrigger>
                  </TabsList>
                  <TabsContent value="text">
                    <Textarea rows={6} placeholder="Nhập nội dung đoạn văn hoặc transcript..." value={contentText} onChange={e => setContentText(e.target.value)} />
                  </TabsContent>
                  <TabsContent value="file">
                    <input type="file" accept="image/*,application/pdf" className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" onChange={e => setContentFile(e.target.files[0])} />
                  </TabsContent>
                </Tabs>
                
                {questionCount > 0 && (
                  <div className="mt-6">
                    <h3 className="font-semibold text-slate-700 mb-3 border-t pt-4 border-slate-100">Đáp án (Answer Key)</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {answerKey.map((ans, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-500 w-6">{i+1}.</span>
                          <Input 
                            value={ans} 
                            onChange={e => {
                              const newKeys = [...answerKey];
                              newKeys[i] = e.target.value;
                              setAnswerKey(newKeys);
                            }} 
                            placeholder="Đáp án"
                            className="h-8 text-sm"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {skill === "speaking" && (
              <div className="space-y-4">
                <Textarea label="Part 1 (Mỗi dòng 1 câu hỏi)" rows={3} value={part1} onChange={e => setPart1(e.target.value)} placeholder="What is your name?&#10;Where are you from?" />
                <Textarea label="Part 2 (Cue Card)" rows={4} value={part2} onChange={e => setPart2(e.target.value)} placeholder="Describe a memorable journey you have made..." />
                <Textarea label="Part 3 (Follow-up)" rows={3} value={part3} onChange={e => setPart3(e.target.value)} placeholder="Why do people like traveling?" />
                
                <label className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer">
                  <input type="checkbox" checked={isMock} onChange={e => setIsMock(e.target.checked)} className="w-5 h-5 text-blue-600 rounded" />
                  <div>
                    <p className="font-medium text-slate-800">Chế độ thi thử (Mock Test)</p>
                    <p className="text-sm text-slate-500">Sử dụng mô hình AI 70B chấm điểm chi tiết và khắt khe hơn. Chỉ nên dùng cho bài test quan trọng.</p>
                  </div>
                </label>
              </div>
            )}

            {skill === "writing" && (
              <div className="space-y-4">
                <Select 
                  label="Loại bài (Task Type)" 
                  value={writingTaskType} 
                  onChange={handleWritingTaskTypeChange}
                  options={[
                    { value: "task1", label: "IELTS Writing Task 1" },
                    { value: "task2", label: "IELTS Writing Task 2" }
                  ]}
                />
                
                <Input label="Số từ tối thiểu" type="number" min="0" value={minWords} onChange={e => setMinWords(Number(e.target.value))} />
                
                <Tabs defaultValue="text">
                  <TabsList>
                    <TabsTrigger value="text">Dán Đề (Text)</TabsTrigger>
                    <TabsTrigger value="file">Upload Đề (Ảnh)</TabsTrigger>
                  </TabsList>
                  <TabsContent value="text">
                    <Textarea label="Nội dung đề" rows={6} value={contentText} onChange={e => setContentText(e.target.value)} />
                  </TabsContent>
                  <TabsContent value="file">
                    <input type="file" accept="image/*" className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" onChange={e => setContentFile(e.target.files[0])} />
                  </TabsContent>
                </Tabs>
              </div>
            )}
          </Card>
        </div>

        {/* Right Preview Panel */}
        <div className="w-full md:w-80 hidden lg:block shrink-0">
          <div className="sticky top-6 space-y-4">
            <Card className="p-4 bg-slate-900 text-white shadow-xl">
              <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
                <LayoutDashboard size={18} />
                Tóm tắt bài tập
              </h3>
              <div className="space-y-2 text-sm text-slate-300">
                <div className="flex justify-between">
                  <span>Kỹ năng:</span>
                  <span className="font-medium text-white capitalize">{skill}</span>
                </div>
                <div className="flex justify-between">
                  <span>Tiêu đề:</span>
                  <span className="font-medium text-white truncate w-32 text-right">{title || "..."}</span>
                </div>
                {(skill === "reading" || skill === "listening") && (
                  <div className="flex justify-between">
                    <span>Số câu hỏi:</span>
                    <span className="font-medium text-white">{questionCount}</span>
                  </div>
                )}
                {skill === "writing" && (
                  <div className="flex justify-between">
                    <span>Yêu cầu:</span>
                    <span className="font-medium text-white capitalize">{writingTaskType} ({minWords}+ words)</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Hạn nộp:</span>
                  <span className="font-medium text-white">{deadline ? new Date(deadline).toLocaleDateString('vi-VN') : "Không có"}</span>
                </div>
              </div>
            </Card>
            <Button className="w-full shadow-lg h-12 text-base font-bold" onClick={handleSubmit} disabled={saving}>
              {saving ? <Spinner size="sm" className="text-white" /> : <><Save size={20} className="mr-2" /> Lưu bài tập</>}
            </Button>
          </div>
        </div>
      </div>
      
      {/* Mobile Sticky Button */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t border-slate-200 lg:hidden z-20 shadow-[0_-4px_10px_rgba(0,0,0,0.05)]">
        <Button className="w-full h-12 text-base font-bold shadow-md" onClick={handleSubmit} disabled={saving}>
          {saving ? <Spinner size="sm" className="text-white" /> : <><Save size={20} className="mr-2" /> Lưu bài tập</>}
        </Button>
      </div>
    </div>
  );
}
