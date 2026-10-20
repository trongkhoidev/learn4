import { useEffect, useMemo, useRef, useState } from "react";
import * as speakingApi from "../api.js";

function pause(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    function abort() {
      clearTimeout(timer);
      reject(new DOMException("Request aborted", "AbortError"));
    }
    signal.addEventListener("abort", abort, { once: true });
  });
}

export function useMockController(testId, studentName) {
  const [questions, setQuestions] = useState(null);
  const [session, setSession] = useState(null);
  const [turnIndex, setTurnIndex] = useState(0);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [error, setError] = useState("");
  const [mockResult, setMockResult] = useState(null);
  const [prepStarted, setPrepStarted] = useState(false);
  const [prepRemaining, setPrepRemaining] = useState(60);
  const submissionController = useRef(null);
  const preparationDeadline = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    async function initialize() {
      try {
        const topics = await speakingApi.getSpeakingTopics({ signal: controller.signal });
        const topic = topics.find(item => item.id === testId) || topics[0];
        if (!topic) throw new Error("Chưa có chủ đề Speaking.");
        const fetched = await speakingApi.getSpeakingQuestions(topic.id, undefined, { signal: controller.signal });
        const part1 = fetched.filter(item => item.part === 1);
        const part2 = fetched.filter(item => item.part === 2).slice(0, 1);
        const part3 = fetched.filter(item => item.part === 3);
        if (!part1.length || !part2.length || !part3.length) {
          throw new Error("Mock test cần có câu hỏi ở đủ cả ba Part.");
        }
        const form = new FormData();
        form.append("student_name", studentName);
        form.append("topic_id", topic.id);
        const created = await speakingApi.startSpeakingMock(form, { signal: controller.signal });
        if (!controller.signal.aborted) {
          setQuestions({ topic, turns: [...part1, ...part2, ...part3] });
          setSession(created);
        }
      } catch (error) {
        if (!controller.signal.aborted) setError(error.message || "Không thể tạo Mock Test.");
      }
    }
    initialize();
    return () => controller.abort();
  }, [testId, studentName]);

  useEffect(() => () => {
    submissionController.current?.abort();
    submissionController.current = null;
  }, []);

  const current = questions?.turns?.[turnIndex] || null;
  const part = current?.part || 1;
  const totalTurns = questions?.turns?.length || 0;

  useEffect(() => {
    preparationDeadline.current = null;
    setPrepStarted(false);
    setPrepRemaining(60);
  }, [turnIndex]);

  useEffect(() => {
    if (part !== 2 || !prepStarted || !preparationDeadline.current) return undefined;
    const updateRemaining = () => {
      const remaining = Math.max(0, Math.ceil((preparationDeadline.current - Date.now()) / 1000));
      setPrepRemaining(remaining);
      return remaining;
    };
    if (updateRemaining() === 0) return undefined;
    const timer = setInterval(() => {
      if (updateRemaining() === 0) clearInterval(timer);
    }, 1000);
    return () => clearInterval(timer);
  }, [part, prepStarted, turnIndex]);

  const progress = useMemo(
    () => totalTurns ? Math.round(((turnIndex + 1) / totalTurns) * 100) : 0,
    [turnIndex, totalTurns],
  );

  function startPreparation() {
    preparationDeadline.current = Date.now() + 60_000;
    setPrepRemaining(60);
    setPrepStarted(true);
  }

  async function waitForTurn(turnId, controller) {
    const deadline = Date.now() + 240000;
    while (Date.now() < deadline) {
      await pause(1000, controller.signal);
      const refreshed = await speakingApi.getSpeakingMock(session.id, { signal: controller.signal });
      if (controller.signal.aborted) return null;
      setSession(refreshed);
      const turn = refreshed.turns.find(item => item.id === turnId);
      if (turn && !["pending", "processing"].includes(turn.status)) return turn;
    }
    throw new Error("Hệ thống chấm quá thời gian. Bạn có thể xem lại session sau.");
  }

  async function handleRecordingComplete(blob) {
    if (!session || !current) return;
    submissionController.current?.abort();
    const controller = new AbortController();
    submissionController.current = controller;
    setIsEvaluating(true);
    setError("");
    try {
      const form = new FormData();
      form.append("part", String(part));
      form.append("question_id", current.id);
      form.append("question_text", current.question_text);
      form.append("file", blob, "audio.webm");
      const submitted = await speakingApi.submitSpeakingMockTurn(session.id, form, { signal: controller.signal });
      const graded = await waitForTurn(submitted.id, controller);
      if (!graded) return;
      if (graded.result?.status === "failed" || graded.result?.status === "needs_review") {
        setError(graded.result?.fluency?.feedback || "Câu trả lời cần nghe lại hoặc ghi âm lại trước khi tiếp tục.");
        return;
      }
      if (turnIndex + 1 < totalTurns) {
        setTurnIndex(index => index + 1);
      } else {
        const completed = await speakingApi.completeSpeakingMock(session.id, { signal: controller.signal });
        setSession(completed);
        const result = completed.result;
        if (!result) throw new Error("Phiên mock chưa có kết quả tổng hợp.");
        setMockResult({
          overall: result.overall,
          pronunciation: { score: result.pronun?.band ?? result.pronun?.score ?? null, status: result.pronun?.status },
          fluency: { score: result.fluency?.band ?? result.fluency?.score ?? null, status: result.fluency?.status },
          grammar: { score: result.grammar?.band ?? result.grammar?.score ?? null, status: result.grammar?.status },
          vocabulary: { score: result.vocab?.band ?? result.vocab?.score ?? null, status: result.vocab?.status },
        });
      }
    } catch (error) {
      if (!controller.signal.aborted) setError(error.message || "Không thể chấm câu trả lời.");
    } finally {
      if (submissionController.current === controller) {
        submissionController.current = null;
        setIsEvaluating(false);
      }
    }
  }

  return {
    questions, session, turnIndex, isEvaluating, error, mockResult, prepStarted,
    startPreparation, prepRemaining, current, part, totalTurns, progress, handleRecordingComplete,
  };
}
