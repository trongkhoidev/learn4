import * as assignmentApi from "../api.js";
import * as submissionApi from "../../submissions/api.js";
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useToast } from "../../../shared/ui/Toast";
import { Card } from "../../../shared/ui/Card";
import { Button } from "../../../shared/ui/Button";
import { ProgressBar } from "../../../shared/ui/ProgressBar";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../../shared/ui/Tabs";
import { ArrowLeft, CheckCircle2, Clock, Send, Mic } from "lucide-react";
import AnswerGrid from "../../submissions/components/AnswerGrid.jsx";
import AudioRecorder from "../components/AudioRecorder.jsx";
import FeedbackPanel from "../../submissions/components/FeedbackPanel.jsx";
import ReasoningCards from "../../submissions/components/ReasoningCards.jsx";
import WritingEditor from "../../writing/components/WritingEditor.jsx";
import WritingResult from "../../writing/components/WritingResult.jsx";

function pollUntilGraded(id, ms = 2000, timeout = 180000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const s = await submissionApi.getSubmission(id);
        if (s.status === "graded") resolve(s);
        else if (Date.now() - start > timeout) reject(new Error("Quá thời gian chờ chấm"));
        else setTimeout(tick, ms);
      } catch (e) {
        reject(e);
      }
    };
    tick();
  });
}

export default function DoAssignment() {
  const { classId, assignmentId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [assignment, setAssignment] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [essay, setEssay] = useState("");
  const [image, setImage] = useState(null);
  
  // Speaking state (per part)
  const [activeTab, setActiveTab] = useState("part1");
  const [audios, setAudios] = useState({});
  const [results, setResults] = useState({});
  const [submittingPart, setSubmittingPart] = useState(null);

  const name = localStorage.getItem(`student_name_${classId}`) || "Học viên";

  useEffect(() => {
    assignmentApi.getAssignment(assignmentId).then(data => {
      setAssignment(data);
      if (data.skill === "speaking" && data.speaking_parts) {
        if (data.speaking_parts.part1) setActiveTab("part1");
        else if (data.speaking_parts.part2) setActiveTab("part2");
        else if (data.speaking_parts.part3) setActiveTab("part3");
      }
    }).catch(e => {
      toast.error("Không tải được đề: " + e.message);
    });
  }, [assignmentId, toast]);

  async function submit(speakingPart = null, speakingAudio = null) {
    const part = speakingPart || "main";
    setSubmittingPart(part);
    
    try {
      const fd = new FormData();
      fd.append("student_name", name);
      let sub;
      
      if (assignment.skill === "reading" || assignment.skill === "listening") {
        fd.append("answers", JSON.stringify(answers));
        sub = await submissionApi.submit(assignmentId, fd);
      } else if (assignment.skill === "speaking") {
        const audioFile = speakingAudio || audios[part];
        if (!audioFile) throw new Error("Hãy ghi âm trước khi nộp");
        
        let questionText = assignment.speaking_parts?.part1 || "";
        let taskType = "PART 1";
        
        if (part === "part2") {
          questionText = assignment.speaking_parts?.part2 || "";
          taskType = "PART 2";
        } else if (part === "part3") {
          questionText = assignment.speaking_parts?.part3 || "";
          taskType = "PART 3";
        }
        
        fd.append("question", questionText);
        fd.append("task_type", taskType);
        fd.append("audio_file", audioFile, "recording.webm");
        
        sub = await submissionApi.submit(assignmentId, fd);
        toast.info("Bài nộp đang được AI phân tích...");
        sub = await pollUntilGraded(sub.id);
      } else {
        fd.append("essay_text", essay || "");
        if (image) fd.append("image_file", image);
        sub = await submissionApi.submit(assignmentId, fd);
        toast.info("Đang chấm bài Writing...");
        sub = await pollUntilGraded(sub.id);
      }
      
      setResults(prev => ({ ...prev, [part]: sub }));
      toast.success("Nộp bài thành công!");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSubmittingPart(null);
    }
  }

  if (!assignment) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const isReading = assignment.skill === "reading" || assignment.skill === "listening";
  
  // Calculate progress for reading/listening
  const answeredCount = answers.filter(a => a && a.trim() !== "").length;
  const totalQuestions = assignment.question_count || 0;
  
  const currentResult = assignment.skill === "speaking" ? results[activeTab] : results["main"];

  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-in fade-in duration-500 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(`/student/${classId}`)} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
            <ArrowLeft size={24} className="text-slate-600" />
          </button>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-100 px-2 py-0.5 rounded">
                {assignment.skill}
              </span>
              {assignment.deadline && (
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock size={12} /> Hạn: {new Date(assignment.deadline).toLocaleString('vi-VN')}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-slate-800">{assignment.title}</h1>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Content */}
        <div className={`${assignment.skill === 'speaking' ? 'lg:col-span-8' : 'lg:col-span-7'} space-y-4`}>
          <Card className="flex flex-col h-[calc(100vh-200px)] border-slate-200 shadow-sm overflow-hidden">
            <div className="bg-slate-50 px-5 py-3 border-b border-slate-100 font-semibold text-slate-700">
              Nội dung đề bài
            </div>
            <div className="p-6 overflow-y-auto flex-1">
              {assignment.audio_url && (
                <div className="mb-6 bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <audio controls src={assignment.audio_url} className="w-full" />
                </div>
              )}
              
              {assignment.skill === "speaking" ? (
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="mb-6">
                    {assignment.speaking_parts?.part1 && <TabsTrigger value="part1">Part 1</TabsTrigger>}
                    {assignment.speaking_parts?.part2 && <TabsTrigger value="part2">Part 2</TabsTrigger>}
                    {assignment.speaking_parts?.part3 && <TabsTrigger value="part3">Part 3</TabsTrigger>}
                  </TabsList>
                  
                  {['part1', 'part2', 'part3'].map(part => {
                    if (!assignment.speaking_parts?.[part]) return null;
                    const isSubmitting = submittingPart === part;
                    const hasResult = !!results[part];
                    
                    return (
                      <TabsContent key={part} value={part} className="space-y-6">
                        <div className="p-6 bg-blue-50/50 border border-blue-100 rounded-xl">
                          <h3 className="text-sm font-bold uppercase text-blue-800 mb-2">
                            {part === 'part2' ? 'Cue Card' : 'Questions'}
                          </h3>
                          <p className="text-slate-800 text-lg leading-relaxed whitespace-pre-wrap font-medium">
                            {assignment.speaking_parts[part]}
                          </p>
                        </div>
                        
                        {!hasResult && (
                          <div className="p-6 border border-slate-200 rounded-xl bg-white shadow-sm text-center">
                            <h3 className="font-semibold text-slate-700 mb-4 flex justify-center items-center gap-2">
                              <Mic size={20} className="text-red-500" /> Ghi âm câu trả lời
                            </h3>
                            <AudioRecorder onReady={(blob) => setAudios(prev => ({ ...prev, [part]: blob }))} />
                            {audios[part] && (
                              <div className="mt-6">
                                <Button 
                                  className="w-full text-base h-12 shadow-md"
                                  onClick={() => submit(part)}
                                  disabled={isSubmitting}
                                >
                                  {isSubmitting ? "Đang nộp..." : <><Send size={20} className="mr-2" /> Nộp bài {part}</>}
                                </Button>
                              </div>
                            )}
                          </div>
                        )}
                      </TabsContent>
                    );
                  })}
                </Tabs>
              ) : (
                <div className="prose prose-slate max-w-none text-slate-700 whitespace-pre-wrap">
                  {assignment.content_text && <div className="text-base leading-relaxed">{assignment.content_text}</div>}
                  {assignment.content_file_url && (
                    <img src={assignment.content_file_url} className="mt-4 rounded-lg border border-slate-200 w-full" alt="Đề bài" />
                  )}
                  {!assignment.content_text && !assignment.content_file_url && !assignment.audio_url && (
                    <p className="text-slate-400 italic">Không có nội dung đính kèm.</p>
                  )}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Answer */}
        {assignment.skill !== "speaking" && (
          <div className="lg:col-span-5 space-y-4">
            <Card className="flex flex-col h-[calc(100vh-200px)] border-slate-200 shadow-sm overflow-hidden relative">
              <div className="bg-slate-50 px-5 py-3 border-b border-slate-100 flex justify-between items-center z-10">
                <h2 className="font-semibold text-slate-700">Bài làm</h2>
                {isReading && (
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <span className="text-blue-600">{answeredCount}/{totalQuestions}</span>
                  </div>
                )}
              </div>
              
              {isReading && (
                <div className="px-5 pt-3 pb-0 z-10 bg-white">
                  <ProgressBar value={answeredCount} max={totalQuestions} className="bg-slate-100" />
                </div>
              )}
              
              <div className="p-5 flex-1 overflow-y-auto">
                {isReading ? (
                  <AnswerGrid count={assignment.question_count} onChange={setAnswers} />
                ) : (
                  <WritingEditor 
                    onEssayChange={setEssay} 
                    onImageChange={setImage} 
                    minWords={assignment.min_words || (assignment.writing_task_type === 'task1' ? 150 : 250)}
                  />
                )}
              </div>
              
              {/* Sticky Footer */}
              <div className="p-5 bg-white border-t border-slate-100 shadow-[0_-4px_10px_rgba(0,0,0,0.02)] z-10">
                <Button 
                  className="w-full text-base h-12 shadow-md"
                  onClick={() => submit()}
                  disabled={!!submittingPart || !!currentResult}
                  variant={currentResult ? "outline" : "primary"}
                >
                  {submittingPart === "main" ? (
                    "Đang nộp..."
                  ) : currentResult ? (
                    <><CheckCircle2 size={20} className="mr-2 text-green-500" /> Đã nộp bài</>
                  ) : (
                    <><Send size={20} className="mr-2" /> Nộp bài</>
                  )}
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Results Modal/Panel */}
      {currentResult && (
        <Card className="border-green-200 shadow-lg overflow-hidden animate-in slide-in-from-bottom-8 duration-500 mt-8">
          <div className="bg-green-50 px-6 py-4 border-b border-green-100 flex items-center gap-3">
            <CheckCircle2 className="text-green-600" size={24} />
            <h2 className="text-lg font-bold text-green-900">Kết quả đánh giá {assignment.skill === 'speaking' && `(${activeTab})`}</h2>
          </div>
          <div className="p-6 bg-white">
            {isReading ? (
              <div className="flex flex-col items-center justify-center py-8">
                <div className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Điểm số của bạn</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-7xl font-black text-green-600">{currentResult.score}</span>
                  <span className="text-3xl font-bold text-slate-300">/ {currentResult.result?.total ?? assignment.question_count}</span>
                </div>
              </div>
            ) : assignment.skill === "speaking" ? (
              <div className="space-y-8 max-w-4xl mx-auto">
                <FeedbackPanel result={currentResult.result} />
                {currentResult.result?.grammar?.errors && (
                  <ReasoningCards errors={currentResult.result.grammar.errors} />
                )}
              </div>
            ) : (
              <div className="max-w-4xl mx-auto">
                <WritingResult result={currentResult.result} />
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
