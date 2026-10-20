# Design System: LexiLearn Academic Operations

> **Cập nhật 2026-10-19:** Hướng navy đồng nhất bên dưới đã bị người dùng từ chối sau khi review Stitch. Ưu tiên UI hiện có trong `frontend` và [quy tắc tối giản](docs/design/simplification-review.md): Speaking giữ nav ngang blue/violet; giáo viên giữ sidebar xanh rêu; không đổi shell/font hoặc hiển thị toàn bộ phân tích cùng lúc. Phần mô tả nghiệp vụ bên dưới chỉ là tham khảo, không phải đặc tả visual hiện hành.

## 1. Visual Theme & Atmosphere

LexiLearn is a formal, focused learning and assessment workspace for an English center. The interface should be calm, clear, and easy to learn. Keep screens task-oriented: show the current class or assignment, the information needed for the current step, and one clear next action. Avoid decorative content and long explanatory copy. The system manages classes, learning materials, assignments, grades, and score progress. It does not manage attendance.

## 2. Color Palette & Roles

- **Cool Canvas** (`#F5F7FA`) — quiet page background.
- **White Surface** (`#FFFFFF`) — forms, tables, passages, and work areas.
- **Deep Navy** (`#17365D`) — primary text, navigation, and high-contrast actions.
- **Academic Blue** (`#2F65A7`) — the single accent for primary buttons, links, focus, and selected states.
- **Pale Blue** (`#EAF1F8`) — selected rows and low-emphasis information surfaces.
- **Slate Text** (`#526174`) — secondary copy, helper text, dates, and metadata.
- **Rule Line** (`#DCE3EB`) — borders and table dividers.
- **Alert Clay** (`#A94F3D`) — errors and overdue states only; pair with a clear text label.

Blue is the product's primary color family. Keep status colors muted and semantic. Never convey a state by color alone. Avoid neon, gradients, glow, pure black, and unrelated accent colors.

## 3. Typography Rules

- **Interface and headings:** Geist Sans with a restrained size and weight hierarchy.
- **Numbers and identifiers:** Geist Mono for class codes, dates, assignment IDs, and rubric values.
- Body and question text should remain comfortable to read, with relaxed line height and a useful line length. Do not shrink text to fit dense panels; simplify or rearrange the content instead.
- Support Vietnamese diacritics. Use sans-serif throughout the product interface.

## 4. Component Stylings

- **Navigation:** role-specific labeled navigation. Keep the current role and selected page obvious; hide links the role cannot use.
- **Buttons:** minimum 44px target, 8px corners, Academic Blue for the single primary action, outlined or text style for secondary actions, visible keyboard focus.
- **Forms:** persistent label above each input, concise helper/error text below, and grouped steps with a small progress indicator.
- **Tables:** readable row height, clear labels, filters close to their table, scores aligned consistently, and no horizontal overflow on small screens.
- **Panels:** white surface, thin Rule Line border, 8–12px corners. Use whitespace and dividers before adding nested cards.
- **Statuses:** use concise text and a restrained icon/fill. Assignment lifecycle: Nháp → Chờ duyệt → Đã giao → Đang làm → Đã nộp → Chờ chấm → Đã trả.
- **Scores:** separate raw/criterion scores, AI suggestions, and teacher-approved scores. Label provisional practice estimates clearly; never imply official IELTS certification.
- **AI feedback:** label as an AI suggestion, link it to evidence from the student's own response/audio, show uncertainty, and provide a human review or learner choice.
- **Loading and empty states:** use layout-matched skeletons. Explain empty states briefly and offer one relevant next action.

## 5. Layout Principles

Use a 248px desktop navigation rail and a content maximum near 1440px. Keep a page title, current class/assignment context, and one primary action together. Show only data needed to complete the current task. Put filters beside their list, and score trends beside the relevant class or learner. On narrow screens, collapse to one column, retain comfortable targets, and avoid horizontal scrolling. For assessment attempts, keep the reading/listening material and question controls legible, with save and submit status easy to find.

## 6. Motion & Interaction

Use restrained transitions for selection, save confirmation, and assignment status changes. Respect reduced-motion preferences. No perpetual animation or decorative motion during reading, listening, recording, and grading.

## 7. Product Structure & Role Responsibilities

### Admin — academic setup and score oversight

1. **Overview:** active term, levels/classes, assignment completion, grade averages, score distribution, and four-skill learning trends. Every metric links to the records behind it. No attendance figures.
2. **Levels and classes:** configure CEFR/program levels, classes within each level, schedules, capacity, teacher assignments, and enrollment. Show class score summaries and assignment completion.
3. **Students:** searchable directory and learner profile with enrollment history, current classes, assignment history, four-skill scores, criterion feedback, and score progression.
4. **Teachers:** directory, expertise, assigned classes, grading queue, and grading turnaround. Do not track attendance or teaching hours as a center outcome.
5. **Curriculum:** organize courses into units and lessons, map activities to Reading/Listening/Speaking/Writing, and attach PDFs, audio, transcripts, and answer keys with source/version information.
6. **Reports and settings:** class/level score trends, assessment outcomes, completion, rubrics, academic terms, role access, notification rules, AI confidence thresholds, and audit trail.

### Teacher — prepare, publish, grade, and return work

1. **Home:** classes taught, assignments to draft/publish, submissions waiting for review, grading queue, and learners whose scores need follow-up. No attendance dashboard.
2. **Class workspace:** roster, course units, materials, assignment statuses, and per-student scores by four skills. The teacher can open a learner's results directly from the roster.
3. **Assignment creation:** select class or unit → choose skill → upload material or author questions manually → choose exercise type manually or request AI recognition → review and edit every question/answer key → preview as student → set due date → publish. Supported objective formats include multiple choice, true/false/not given, matching, ordering, gap fill, and short answer. AI recognition is optional; it never publishes directly.
4. **Submission queue:** filter by class, assignment, skill, status, and due date. Open an individual submission; show when it was submitted and whether it needs a human check.
5. **Reading/Listening grading:** compare objective answers with the teacher-approved answer key. Automatically score clear objective items. Route ambiguous, missing, or disputed answers to teacher review; allow an override with a short note.
6. **Writing grading:** review prompt and essay beside Task Response, Coherence & Cohesion, Lexical Resource, and Grammar scores. AI suggestions must cite exact text. Teacher sets final criterion scores and feedback, then approves and releases the result.
7. **Speaking grading:** play the original audio, inspect time-aligned transcript/confidence flags, and replay uncertain segments. AI may propose criterion feedback only from reliable evidence. Teacher sets final Fluency & Coherence, Lexical Resource, Grammar, and Pronunciation scores, adds feedback, and either approves/releases or requests a re-recording. Low-confidence audio must not be scored as a definite pronunciation error.

### Student — complete work and use score feedback

1. **Home:** current classes, due assignments grouped by skill, latest returned scores/feedback, score trends, and one clear continue action. No attendance figures.
2. **Class page:** teacher, schedule, announcements, unit roadmap, learning materials, assignments, and the student's four-skill scores.
3. **Reading/Listening:** open instructions → complete questions with autosave and question navigation → mark items for review → review answers → confirm submission. Show submitted/waiting-for-review status. Reveal scores and answer feedback only according to the assignment's release settings.
4. **Writing:** open prompt → write in a simple editor with word count and autosave/version history → optionally review AI suggestions tied to exact sentences → accept, edit, or ignore suggestions → submit → wait for teacher review.
5. **Speaking:** review prompt and recording instructions → record → listen back and re-record if allowed → inspect transcript and correct uncertain recognition → submit → wait for teacher review. Show pronunciation practice feedback only when audio confidence is sufficient.
6. **Results:** show teacher-approved skill and criterion scores, concise evidence-based feedback, history/trend, and one suggested next practice task. Clearly distinguish any provisional practice estimate from an official exam result.

## 8. End-to-End Flows

### Assignment creation and publication

Teacher selects a class/unit and skill → chooses upload/manual authoring or optional AI recognition → checks and edits questions and answer key → previews as a student → sets due date and target class → publishes. Each state has one owner and one primary next action.

### Student attempt and objective scoring

Student opens instructions → answers with autosave → reviews flagged/unanswered questions → confirms submission → sees “Đã nộp / Chờ chấm” → clear objective answers are scored against the teacher-approved key → ambiguous/disputed items enter the teacher queue → score is released under the assignment's feedback policy.

### Writing

Student drafts and optionally uses evidence-linked AI suggestions → student chooses whether to apply them → submits → teacher reviews essay and rubric evidence → teacher sets criterion scores and feedback → teacher approves/releases → student views scores, comments, and next practice.

### Speaking

Student reviews prompt and recording guidance → records and reviews playback/transcript → corrects uncertain transcript → submits → AI highlights only reliable evidence and uncertainty → teacher listens to flagged audio, sets rubric scores and feedback → teacher approves/releases or requests a re-recording → student views approved result and next practice.

### Admin oversight

Admin configures levels, classes, teachers, and curriculum → teachers publish assignments and return grades → admin reviews aggregate class/level and four-skill score trends. Admin reporting does not include attendance.

The interface must always show the current owner, current status, and next action. AI can assist with recognition and feedback but cannot publish an assignment, decide ambiguous objective answers, or finalize Writing/Speaking grades on its own.

## 9. Anti-Patterns (Banned)

- No attendance tracking or attendance metrics.
- No flashy effects, decorative gradients, neon, glow, pure black, or multiple competing accent colors.
- No equal three-column oversized KPI cards, excessive nesting, redundant explanations, fake technical artifacts, or dense filler text.
- No status shown only through color; no unsupported official score claims; no final AI-only Writing/Speaking score.
- No scoring pronunciation from uncertain audio and no untraceable AI feedback.
- No hidden labels, tiny controls, horizontal page scrolling, or multiple equally prominent primary actions on one screen.
