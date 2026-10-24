# Design System Specification (Stitch Design) — LexiLearn Speaking Studio

## 1. Design Vision & Philosophy
The Speaking Studio interface provides learners with an executive, encouraging, and authoritative IELTS examiner experience. It replaces cold engineering telemetry with a polished, human-centric, and goal-oriented learning dashboard.

- **Authoritative & Trustworthy**: Clear, calibrated IELTS band scoring that students can rely on.
- **Cognitive Clarity**: Progressive disclosure — students see the big picture (Overall Band & 4 Criteria) immediately, followed by actionable deep dives (Transcript, Errors, Model Answer).
- **Zero Distraction / No Pipeline Slop**: Internal engineering telemetry (such as "Độ phủ bằng chứng", ASR disagreement metrics, or provider counts) is completely stripped from learner-facing views.

---

## 2. Color Palette & Semantics

| Token | Class / Hex | Semantic Meaning |
|---|---|---|
| **Background** | `bg-slate-50/70` | Neutral, calming background canvas |
| **Card Surface** | `bg-white` with `border border-slate-100 shadow-sm` | Clean elevation for content cards |
| **Hero Surface** | `bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900` | Luxury, high-contrast dark surface for Overall Band |
| **Fluency & Coherence** | Accent Blue: `bg-blue-50 text-blue-700 border-blue-200` | Continuity, pacing, natural flow |
| **Lexical Resource** | Accent Violet: `bg-violet-50 text-violet-700 border-violet-200` | Vocabulary richness, collocations |
| **Grammatical Range & Accuracy** | Accent Emerald: `bg-emerald-50 text-emerald-700 border-emerald-200` | Structure precision, correct grammar |
| **Pronunciation** | Accent Amber: `bg-amber-50 text-amber-700 border-amber-200` | Intonation, clarity, stress |

---

## 3. Typography & Hierarchy
- **Header Titles**: `text-2xl` / `text-3xl font-extrabold tracking-tight text-slate-900`
- **Section Headers**: `text-lg font-bold text-slate-800`
- **Scores**: `text-4xl font-black tracking-tight` for Overall, `text-2xl font-black` for criteria
- **Body & Explanations**: `text-sm leading-relaxed text-slate-600`
- **Badges & Labels**: `text-xs font-bold tracking-wide uppercase px-2.5 py-1 rounded-full`

---

## 4. Component Standards

### A. Score Board (Hero & 4-Criteria Grid)
- **Hero Card**: Bold numerical Overall score, official IELTS descriptor label (e.g. "Good User / Competent User"), and examiner summary.
- **Criteria Grid**: 4 equal-width responsive cards with accent headers, score pills, and quick strengths/improvements.

### B. Interactive Audio & Color-coded Transcript
- Word confidence badges with smooth playback sync.
- Click-to-listen for any word or phrase.

### C. Actionable Feedback Cards
- **Model Answer (Band 8.5+)**: Highlighted collocations, natural sentence structures, and one-click copy.
- **Grammar & Vocabulary Diff**: Clean before/after display (`Lỗi` -> `Sửa lại`: `Giải thích`).
- **Next Practice Drill (Bước luyện tập)**: Concrete, 1-step exercise for the learner's next recording.
