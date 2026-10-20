import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import * as speakingApi from "../api.js";

function pause(ms, signal) {
  return new Promise((resolve, reject) => {
    function abort() {
      clearTimeout(timer);
      reject(new DOMException("Request aborted", "AbortError"));
    }
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}

function fallbackTopics(includeTravel) {
  const topics = [
    { id: "1", name: "Education", description: "Describe your educational background" },
    { id: "2", name: "Technology", description: "Talk about a gadget you use often" },
  ];
  if (includeTravel) topics.push({ id: "3", name: "Travel", description: "Describe a memorable journey" });
  return topics;
}

function practiceResult(assessment, sessionId) {
  return {
    raw: assessment,
    sessionId,
    scores: {
      overall: assessment.overall,
      pronunciation: { score: assessment.pronun?.band ?? assessment.pronun?.score ?? null, status: assessment.pronun?.status },
      fluency: { score: assessment.fluency?.band ?? assessment.fluency?.score ?? null, status: assessment.fluency?.status },
      grammar: { score: assessment.grammar?.band ?? assessment.grammar?.score ?? null, status: assessment.grammar?.status },
      vocabulary: { score: assessment.vocab?.band ?? assessment.vocab?.score ?? null, status: assessment.vocab?.status },
    },
    words: assessment.color_coded_transcript || [],
    errors: assessment.grammar?.errors || [],
  };
}

async function waitForAssessment(response, signal) {
  const deadline = Date.now() + 180000;
  while (response.status === "pending" && Date.now() < deadline) {
    await pause(1000, signal);
    response = await speakingApi.getSpeakingPractice(response.id, { signal });
  }
  if (response.status === "pending") throw new Error("Hệ thống chấm quá thời gian. Kết quả vẫn được lưu trong lịch sử.");
  if (!response.result) throw new Error("Không nhận được kết quả phân tích.");
  return response;
}

export function usePracticeController(routeTopicId) {
  const [searchParams] = useSearchParams();
  const savedSessionId = searchParams.get("session");
  const [step, setStep] = useState(1);
  const [recognitionContext, setRecognitionContext] = useState('');
  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectedPart, setSelectedPart] = useState("PART 2");
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [result, setResult] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [error, setError] = useState("");
  const [prepStarted, setPrepStarted] = useState(false);
  const [prepRemaining, setPrepRemaining] = useState(60);
  const [recordingUrl, setRecordingUrl] = useState(null);
  const submissionController = useRef(null);
  const preparationDeadline = useRef(null);
  const studentName = localStorage.getItem("speaking_name") || "Guest";

  useEffect(() => {
    const controller = new AbortController();
    speakingApi.getSpeakingTopics({ signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return;
      if (data.length > 0) {
        setTopics(data);
        if (routeTopicId) {
          const found = data.find(topic => topic.id === routeTopicId);
          if (found) {
            setSelectedTopic(found);
            setStep(2);
          }
        }
      } else {
        setTopics(fallbackTopics(true));
      }
    }).catch(error => {
      if (controller.signal.aborted) return;
      console.error(error);
      setTopics(fallbackTopics(false));
    });
    return () => controller.abort();
  }, [routeTopicId]);

  useEffect(() => {
    if (!savedSessionId) return undefined;
    const controller = new AbortController();
    setIsEvaluating(true);
    setError("");
    speakingApi.getSpeakingPractice(savedSessionId, { signal: controller.signal })
      .then(response => waitForAssessment(response, controller.signal))
      .then(response => {
        if (controller.signal.aborted) return;
        setResult(practiceResult(response.result, response.id));
        setSelectedTopic({ id: response.topic_id, name: "Bài luyện đã lưu" });
        setSelectedPart(response.part_type || "PART 2");
        setRecordingUrl(response.audio_url || null);
        setStep(3);
      })
      .catch(error => {
        if (!controller.signal.aborted) setError(error.message || "Không mở được bài luyện đã lưu.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsEvaluating(false);
      });
    return () => controller.abort();
  }, [savedSessionId]);

  useEffect(() => {
    if (!selectedTopic?.id) return undefined;
    const controller = new AbortController();
    setQuestionsLoading(true);
    setQuestions([]);
    const part = Number(selectedPart.replace("PART ", ""));
    speakingApi.getSpeakingQuestions(selectedTopic.id, part, { signal: controller.signal })
      .then(data => {
        if (controller.signal.aborted) return;
        setQuestions(data);
        setQuestionIndex(0);
        setQuestionsLoading(false);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setQuestions([]);
        setQuestionIndex(0);
        setQuestionsLoading(false);
      });
    return () => controller.abort();
  }, [selectedTopic?.id, selectedPart]);

  useEffect(() => {
    preparationDeadline.current = null;
    setPrepStarted(false);
    setPrepRemaining(60);
  }, [selectedTopic?.id, selectedPart, questionIndex]);

  useEffect(() => {
    if (selectedPart !== "PART 2" || !prepStarted || !preparationDeadline.current) return undefined;
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
  }, [selectedPart, prepStarted, selectedTopic?.id, questionIndex]);

  useEffect(() => () => {
    submissionController.current?.abort();
    submissionController.current = null;
  }, []);

  const currentQuestion = questions[questionIndex] || null;
  const displayedQuestion = currentQuestion?.question_text || selectedTopic?.description || selectedTopic?.name || "";
  const isPart2 = selectedPart === "PART 2";
  const recorderReady = !questionsLoading && (!isPart2 || (prepStarted && prepRemaining === 0));

  function startPreparation() {
    preparationDeadline.current = Date.now() + 60_000;
    setPrepRemaining(60);
    setPrepStarted(true);
  }

  function resetPreparation() {
    preparationDeadline.current = null;
    setPrepStarted(false);
    setPrepRemaining(60);
  }

  async function handleRecordingComplete(blob) {
    submissionController.current?.abort();
    const controller = new AbortController();
    submissionController.current = controller;
    setIsEvaluating(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("student_name", studentName);
      formData.append("recognition_context", recognitionContext);
      formData.append("topic_id", selectedTopic.id || "");
      formData.append("part_type", selectedPart);
      if (currentQuestion?.id) formData.append("question_id", currentQuestion.id);
      formData.append("question_text", displayedQuestion);
      formData.append("file", blob, "audio.webm");
      formData.append("async_processing", "true");
      setRecordingUrl(URL.createObjectURL(blob));

      const submitted = await speakingApi.submitSpeakingPractice(formData, { signal: controller.signal });
      const response = await waitForAssessment(submitted, controller.signal);
      setResult(practiceResult(response.result, response.id));
      setStep(3);
    } catch (error) {
      if (controller.signal.aborted) return;
      console.error(error);
      setError(error.message || "Đã xảy ra lỗi khi chấm điểm. Vui lòng thử lại.");
    } finally {
      if (submissionController.current === controller) {
        submissionController.current = null;
        setIsEvaluating(false);
      }
    }
  }

  async function saveReviewDecision(decision) {
    if (!result?.sessionId) throw new Error("Không tìm thấy bài luyện để lưu.");
    const response = await speakingApi.saveTranscriptReview(result.sessionId, {
      ...decision, student_name: studentName,
    });
    setResult(practiceResult(response.result, response.id));
  }

  return {
    recognitionContext, setRecognitionContext, saveReviewDecision,
    step, setStep, topics, selectedTopic, setSelectedTopic, selectedPart, setSelectedPart,
    isEvaluating, result, setResult, questions, questionsLoading, questionIndex, setQuestionIndex, error,
    setError, prepStarted, startPreparation, resetPreparation, prepRemaining, recordingUrl,
    currentQuestion, displayedQuestion, isPart2, recorderReady, handleRecordingComplete,
  };
}
