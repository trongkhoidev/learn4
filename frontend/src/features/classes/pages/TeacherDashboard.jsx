import * as classApi from "../api.js";
import * as assignmentApi from "../../assignments/api.js";
import * as submissionApi from "../../submissions/api.js";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../../shared/ui/Button";
import { Input } from "../../../shared/ui/Input";
import { Modal } from "../../../shared/ui/Modal";
import { ConfirmDialog } from "../../../shared/ui/ConfirmDialog";
import { useToast } from "../../../shared/ui/Toast";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { BookOpen, ClipboardCheck, Users, FileText, Copy, Edit, Trash2, Plus, ArrowUpRight, Search, ChevronRight, Clock3, Headphones, Mic2, PenLine, BookMarked } from "lucide-react";

const SKILLS = [
  { key: "reading", label: "Reading", Icon: BookMarked },
  { key: "listening", label: "Listening", Icon: Headphones },
  { key: "speaking", label: "Speaking", Icon: Mic2 },
  { key: "writing", label: "Writing", Icon: PenLine },
];

const EMPTY_FORM = { name: "", level: "General English B1", teacher_note: "" };

export default function Dashboard() {
  const [code, setCode] = useState(localStorage.getItem("teacher_code") || "");
  const [authed, setAuthed] = useState(!!localStorage.getItem("teacher_code"));
  const [loading, setLoading] = useState(false);
  const [classes, setClasses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [filter, setFilter] = useState("Tất cả cấp độ");
  const [query, setQuery] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [classToEdit, setClassToEdit] = useState(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [classToDelete, setClassToDelete] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const { toast } = useToast();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const classList = await classApi.listClasses();
      const perClass = await Promise.all(classList.map(async (cls) => {
        const classAssignments = await assignmentApi.listAssignments(cls.id);
        const classSubmissions = await Promise.all(classAssignments.map((assignment) => submissionApi.listSubmissions(assignment.id)));
        return {
          cls,
          assignments: classAssignments,
          submissions: classSubmissions.flat().map((submission) => ({ ...submission, class_id: cls.id, class_name: cls.name })),
        };
      }));
      setClasses(classList);
      setAssignments(perClass.flatMap((item) => item.assignments.map((assignment) => ({ ...assignment, class_name: item.cls.name, level: item.cls.level || "General English B1" }))));
      setSubmissions(perClass.flatMap((item) => item.submissions));
      setError("");
    } catch (e) {
      if (e.message.includes("403")) {
        setAuthed(false);
        localStorage.removeItem("teacher_code");
      }
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (authed) loadData(); }, [authed, loadData]);

  const levelRows = useMemo(() => {
    const groups = new Map();
    classes.forEach((cls) => {
      const level = cls.level || "General English B1";
      groups.set(level, (groups.get(level) || 0) + 1);
    });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [classes]);

  const enrollmentCount = new Set(submissions.map((item) => `${item.class_id}:${item.student_name?.trim().toLowerCase()}`)).size;
  const pending = submissions.filter((item) => item.status === "pending");
  const filteredClasses = classes.filter((cls) => {
    const matchesLevel = filter === "Tất cả cấp độ" || (cls.level || "General English B1") === filter;
    const matchesQuery = `${cls.name} ${cls.level || ""}`.toLowerCase().includes(query.toLowerCase());
    return matchesLevel && matchesQuery;
  });
  const skillCounts = SKILLS.map((skill) => ({ ...skill, count: assignments.filter((item) => item.skill === skill.key).length }));
  const totalAssignments = assignments.length || 0;

  function login() {
    localStorage.setItem("teacher_code", code);
    setAuthed(true);
  }

  async function handleCreate() {
    if (!formData.name.trim() || !formData.level.trim()) return;
    try {
      await classApi.createClass(formData.name.trim(), formData.teacher_note.trim(), formData.level.trim());
      toast.success("Đã tạo lớp học mới!");
      setIsCreateOpen(false);
      setFormData(EMPTY_FORM);
      loadData();
    } catch (e) { toast.error(e.message); }
  }

  async function handleEdit() {
    if (!formData.name.trim() || !formData.level.trim()) return;
    try {
      await classApi.updateClass(classToEdit.id, { name: formData.name.trim(), level: formData.level.trim(), teacher_note: formData.teacher_note.trim() });
      toast.success("Đã cập nhật lớp học!");
      setIsEditOpen(false);
      setClassToEdit(null);
      loadData();
    } catch (e) { toast.error(e.message); }
  }

  async function handleDelete() {
    try {
      await classApi.deleteClass(classToDelete.id);
      toast.success("Đã xóa lớp học và dữ liệu bài tập liên quan.");
      setIsDeleteOpen(false);
      setClassToDelete(null);
      loadData();
    } catch (e) { toast.error(e.message); }
  }

  function copyCode(codeStr, event) {
    event.preventDefault();
    event.stopPropagation();
    navigator.clipboard.writeText(`${window.location.origin}/join?code=${codeStr}`);
    toast.info("Đã sao chép liên kết mời lớp.");
  }

  if (!authed) {
    return (
      <div className="mx-auto flex min-h-[70dvh] max-w-md items-center px-4">
        <section className="w-full rounded-2xl border border-[#e4e8e2] bg-white p-8 shadow-sm">
          <div className="mb-7 flex h-12 w-12 items-center justify-center rounded-xl bg-[#19352c] text-xl font-semibold text-white">L</div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[.15em] text-[#769b83]">LexiLearn · Giáo viên</p>
          <h1 className="text-2xl font-semibold tracking-tight text-[#19352c]">Đăng nhập quản lý</h1>
          <p className="mt-2 text-sm leading-6 text-[#717b75]">Dùng mã truy cập của trung tâm để quản lý cấp độ, lớp học và bài tập.</p>
          <div className="mt-7 space-y-4">
            <Input label="Mã truy cập" type="password" placeholder="Nhập mã giáo viên" value={code} onChange={(event) => setCode(event.target.value)} onKeyDown={(event) => event.key === "Enter" && login()} />
            {error && <p className="text-sm text-[#a94f3d]">{error}</p>}
            <button className="min-h-11 w-full rounded-lg bg-[#19352c] px-5 text-sm font-medium text-white transition hover:bg-[#27483b]" onClick={login}>Vào hệ thống</button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1440px] space-y-7 pb-8 text-[#29332f]">
      <header className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm text-[#717b75]">Thứ Hai · Trung tâm Anh ngữ</p>
          <h1 className="mt-2 text-[clamp(1.7rem,3vw,2.25rem)] font-semibold tracking-[-.04em] text-[#19352c]">Trung tâm tuần này</h1>
          <p className="mt-1 text-sm text-[#717b75]">Theo dõi cấp độ, lớp học và tiến độ bài tập trong một nơi.</p>
        </div>
        <button onClick={() => { setFormData(EMPTY_FORM); setIsCreateOpen(true); }} className="inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-lg bg-[#19352c] px-4 text-sm font-medium text-white transition hover:bg-[#27483b] active:translate-y-px sm:self-auto">
          <Plus size={17} /> Tạo lớp học
        </button>
      </header>

      {error && <div className="rounded-lg border border-[#e6c7bf] bg-[#fbf1ee] px-4 py-3 text-sm text-[#8d4032]">Không tải được dữ liệu: {error}</div>}

      <section aria-label="Chỉ số vận hành" className="grid grid-cols-2 gap-3 border-y border-[#e4e8e2] py-4 lg:grid-cols-4 lg:gap-0 lg:divide-x lg:divide-[#e4e8e2]">
        <Metric icon={BookOpen} label="Lớp đang quản lý" value={classes.length} detail={`${levelRows.length} cấp độ`} />
        <Metric icon={Users} label="Lượt học viên đã nộp" value={enrollmentCount} detail="Theo dữ liệu bài nộp" />
        <Metric icon={FileText} label="Bài tập đã giao" value={totalAssignments} detail="Reading · Listening · Speaking · Writing" />
        <Metric icon={ClipboardCheck} label="Bài chờ chấm" value={pending.length} detail={pending.length ? "Cần xem lại và phản hồi" : "Đã xử lý hết bài đang có"} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,.85fr)]">
        <div className="overflow-hidden rounded-xl border border-[#e4e8e2] bg-white">
          <div className="flex flex-col gap-4 border-b border-[#e4e8e2] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-[#19352c]">Lớp học & cấp độ</h2>
              <p className="mt-1 text-sm text-[#717b75]">Các lớp được nhóm theo trình độ tiếng Anh.</p>
            </div>
            <label className="relative block w-full sm:max-w-[220px]">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#87918a]" />
              <input aria-label="Tìm lớp học" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm lớp hoặc cấp độ" className="min-h-10 w-full rounded-lg border border-[#e4e8e2] bg-[#fbfcfa] pl-9 pr-3 text-sm outline-none transition focus:border-[#769b83] focus:ring-2 focus:ring-[#769b83]/20" />
            </label>
          </div>
          <div className="flex gap-2 overflow-x-auto border-b border-[#e4e8e2] px-5 py-3">
            {["Tất cả cấp độ", ...levelRows.map(([level]) => level)].map((level) => (
              <button key={level} onClick={() => setFilter(level)} className={`min-h-9 shrink-0 rounded-full px-3.5 text-xs font-medium transition ${filter === level ? "bg-[#19352c] text-white" : "bg-[#f2f4f0] text-[#58645d] hover:bg-[#eaf1eb]"}`}>{level}{level === "Tất cả cấp độ" ? ` · ${classes.length}` : ` · ${levelRows.find(([key]) => key === level)?.[1] || 0}`}</button>
            ))}
          </div>
          {loading && classes.length === 0 ? (
            <div className="space-y-4 p-5" aria-label="Đang tải lớp học">{[0, 1, 2].map((item) => <div key={item} className="h-12 animate-pulse rounded-md bg-[#f2f4f0]" />)}</div>
          ) : filteredClasses.length ? (
            <div className="divide-y divide-[#e4e8e2]">
              {filteredClasses.map((cls) => {
                const classAssignments = assignments.filter((item) => item.class_id === cls.id);
                const classSubmissions = submissions.filter((item) => item.class_id === cls.id);
                const learners = new Set(classSubmissions.map((item) => item.student_name?.trim().toLowerCase()).filter(Boolean)).size;
                return (
                  <article key={cls.id} className="group flex flex-col gap-3 px-5 py-4 transition hover:bg-[#fbfcfa] sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link to={`/teacher/class/${cls.id}`} className="truncate text-sm font-semibold text-[#19352c] hover:text-[#557961]">{cls.name}</Link>
                        <span className="rounded-md bg-[#eaf1eb] px-2 py-1 text-[11px] font-medium text-[#42624c]">{cls.level || "General English B1"}</span>
                      </div>
                      <p className="mt-1 truncate text-xs text-[#717b75]">{cls.teacher_note || "Chưa có ghi chú lớp học"}</p>
                    </div>
                    <div className="flex items-center justify-between gap-5 sm:justify-end">
                      <div className="text-right"><p className="font-mono text-sm font-medium text-[#29332f]">{learners}</p><p className="text-[11px] text-[#87918a]">học viên</p></div>
                      <div className="text-right"><p className="font-mono text-sm font-medium text-[#29332f]">{classAssignments.length}</p><p className="text-[11px] text-[#87918a]">bài tập</p></div>
                      <div className="flex items-center gap-1">
                        <button title="Sao chép link lớp" aria-label={`Sao chép link ${cls.name}`} onClick={(event) => copyCode(cls.share_code, event)} className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg text-[#717b75] hover:bg-[#eaf1eb] hover:text-[#19352c]"><Copy size={15} /></button>
                        <button title="Sửa lớp" aria-label={`Sửa ${cls.name}`} onClick={() => { setClassToEdit(cls); setFormData({ name: cls.name, level: cls.level || "General English B1", teacher_note: cls.teacher_note || "" }); setIsEditOpen(true); }} className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg text-[#717b75] hover:bg-[#eaf1eb] hover:text-[#19352c]"><Edit size={15} /></button>
                        <Link title="Mở lớp" aria-label={`Mở ${cls.name}`} to={`/teacher/class/${cls.id}`} className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg text-[#557961] hover:bg-[#eaf1eb]"><ChevronRight size={18} /></Link>
                        <button title="Xóa lớp" aria-label={`Xóa ${cls.name}`} onClick={() => { setClassToDelete(cls); setIsDeleteOpen(true); }} className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg text-[#9b6b62] hover:bg-[#fbf1ee]"><Trash2 size={15} /></button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <EmptyState icon={BookOpen} title={classes.length ? "Không tìm thấy lớp phù hợp" : "Bắt đầu với lớp đầu tiên"} description={classes.length ? "Thử đổi cấp độ hoặc từ khóa tìm kiếm." : "Tạo lớp theo trình độ như A2, B1, IELTS 5.5 hoặc giao tiếp thiếu nhi."} action={!classes.length && <Button onClick={() => { setFormData(EMPTY_FORM); setIsCreateOpen(true); }}>Tạo lớp học</Button>} />
          )}
          {classes.length > 0 && <div className="flex items-center justify-between border-t border-[#e4e8e2] px-5 py-3 text-xs text-[#717b75]"><span>{filteredClasses.length} / {classes.length} lớp</span><span className="flex items-center gap-1">Mở sổ lớp <ArrowUpRight size={13} /></span></div>}
        </div>

        <aside className="space-y-5">
          <div className="rounded-xl border border-[#e4e8e2] bg-white p-5">
            <div className="flex items-start justify-between gap-4">
              <div><h2 className="text-base font-semibold text-[#19352c]">Phân bố lớp theo cấp độ</h2><p className="mt-1 text-sm text-[#717b75]">Quy mô lớp học hiện tại</p></div>
              <BookOpen size={18} className="text-[#769b83]" />
            </div>
            {levelRows.length ? <div className="mt-5 space-y-4">{levelRows.map(([level, count]) => <div key={level}>
              <div className="mb-1.5 flex items-center justify-between text-xs"><span className="font-medium text-[#3f4d45]">{level}</span><span className="font-mono text-[#717b75]">{count} lớp</span></div>
              <div className="h-2 overflow-hidden rounded-full bg-[#edf0eb]"><div className="h-full rounded-full bg-[#769b83]" style={{ width: `${Math.max(7, (count / Math.max(1, classes.length)) * 100)}%` }} /></div>
            </div>)}</div> : <p className="mt-5 rounded-lg bg-[#f7f7f2] p-4 text-sm text-[#717b75]">Cấp độ sẽ xuất hiện sau khi bạn tạo lớp đầu tiên.</p>}
          </div>

          <div className="rounded-xl border border-[#e4e8e2] bg-white p-5">
            <div className="flex items-start justify-between gap-4"><div><h2 className="text-base font-semibold text-[#19352c]">Bài tập theo kỹ năng</h2><p className="mt-1 text-sm text-[#717b75]">Số bài đã giao trong các lớp</p></div><ClipboardCheck size={18} className="text-[#769b83]" /></div>
            <div className="mt-4 divide-y divide-[#e4e8e2]">{skillCounts.map(({ key, label, Icon, count }) => <div key={key} className="flex min-h-11 items-center justify-between py-2"><span className="flex items-center gap-2 text-sm text-[#526057]"><Icon size={15} className="text-[#769b83]" />{label}</span><span className="font-mono text-sm font-medium text-[#29332f]">{count}</span></div>)}</div>
            <Link to="/teacher" className="mt-3 inline-flex min-h-10 items-center gap-1 text-sm font-medium text-[#557961] hover:text-[#19352c]">Quản lý bài tập <ArrowUpRight size={15} /></Link>
          </div>

          <div className="rounded-xl border border-[#e4e8e2] bg-white p-5">
            <div className="flex items-start justify-between gap-4"><div><h2 className="text-base font-semibold text-[#19352c]">Cần chấm</h2><p className="mt-1 text-sm text-[#717b75]">Bài đang chờ giáo viên xem</p></div><Clock3 size={18} className="text-[#769b83]" /></div>
            {pending.length ? <div className="mt-4 space-y-3">{pending.slice(0, 3).map((submission) => <div key={submission.id} className="flex items-center justify-between gap-3 border-t border-[#e4e8e2] pt-3"><div className="min-w-0"><p className="truncate text-sm font-medium text-[#3f4d45]">{submission.student_name}</p><p className="truncate text-xs text-[#87918a]">{submission.class_name}</p></div><span className="shrink-0 rounded-full bg-[#f0e9db] px-2.5 py-1 text-[11px] font-medium text-[#806f50]">Chờ chấm</span></div>)}</div> : <p className="mt-4 rounded-lg bg-[#f7f7f2] p-4 text-sm text-[#717b75]">Chưa có bài nộp cần chấm.</p>}
          </div>
        </aside>
      </section>

      <section className="rounded-xl border border-[#e4e8e2] bg-[#edf2ed] p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="text-xs font-semibold uppercase tracking-[.12em] text-[#557961]">Bốn kỹ năng · Một lộ trình</p><h2 className="mt-1 text-lg font-semibold tracking-tight text-[#19352c]">Từ tài liệu đến phản hồi cho học viên</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-[#65736a]">Reading và Listening dùng đáp án giáo viên thiết lập. Speaking và Writing có trợ lý AI, kèm bằng chứng và trạng thái cần xem lại.</p></div>
          <Link to="/teacher" className="inline-flex min-h-10 shrink-0 items-center gap-1 text-sm font-semibold text-[#42624c] hover:text-[#19352c]">Mở sổ bài tập <ArrowUpRight size={15} /></Link>
        </div>
      </section>

      <ClassModal open={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Tạo lớp học mới" formData={formData} setFormData={setFormData} onSave={handleCreate} saveLabel="Tạo lớp" />
      <ClassModal open={isEditOpen} onClose={() => setIsEditOpen(false)} title="Chỉnh sửa lớp học" formData={formData} setFormData={setFormData} onSave={handleEdit} saveLabel="Lưu thay đổi" />
      <ConfirmDialog open={isDeleteOpen} onClose={() => setIsDeleteOpen(false)} title="Xóa lớp học?" message={`Xóa lớp “${classToDelete?.name}” và toàn bộ bài tập, bài nộp liên quan?`} confirmLabel="Xóa lớp" danger onConfirm={handleDelete} />
    </div>
  );
}

function Metric({ icon: Icon, label, value, detail }) {
  return <div className="px-0 py-1 first:pl-0 lg:px-5"><div className="flex items-center gap-2 text-xs font-medium text-[#717b75]"><Icon size={15} className="text-[#769b83]" />{label}</div><div className="mt-2 font-mono text-2xl font-semibold tracking-tight text-[#19352c]">{value}</div><p className="mt-1 text-[11px] text-[#87918a]">{detail}</p></div>;
}

function ClassModal({ open, onClose, title, formData, setFormData, onSave, saveLabel }) {
  return <Modal open={open} onClose={onClose} title={title} footer={<><Button variant="outline" onClick={onClose}>Hủy</Button><Button onClick={onSave}>{saveLabel}</Button></>}>
    <div className="space-y-4">
      <Input label="Tên lớp" placeholder="Ví dụ: IELTS Foundation 03" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} />
      <Input label="Cấp độ / chương trình" placeholder="A2, B1, IELTS 5.5, Tiếng Anh thiếu nhi" value={formData.level} onChange={(event) => setFormData({ ...formData, level: event.target.value })} />
      <Input label="Lịch học hoặc ghi chú (tùy chọn)" placeholder="Ví dụ: Thứ 2–4–6, 18:30" value={formData.teacher_note} onChange={(event) => setFormData({ ...formData, teacher_note: event.target.value })} />
    </div>
  </Modal>;
}
