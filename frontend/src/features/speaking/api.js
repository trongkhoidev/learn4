import { request } from "../../shared/api/transport.js";

export const getSpeakingTopics = ({ signal } = {}) => request("GET", "/speaking/topics", { signal });
export const getSpeakingQuestions = (topicId, part, { signal } = {}) => {
  let url = "/speaking/questions?";
  if (topicId) url += `topic_id=${topicId}&`;
  if (part) url += `part=${part}`;
  return request("GET", url, { signal });
};
export const submitSpeakingPractice = (formData, { signal } = {}) => request("POST", "/speaking/practice", { form: formData, signal });
export const getSpeakingPractice = (id, { signal } = {}) => request("GET", `/speaking/practice/${id}`, { signal });
export const getSpeakingHistory = (studentName) => request("GET", `/speaking/history?student_name=${encodeURIComponent(studentName)}`);
export const getSpeakingProgress = (studentName) => request("GET", `/speaking/progress?student_name=${encodeURIComponent(studentName)}`);
export const startSpeakingMock = (formData, { signal } = {}) => request("POST", "/speaking/mock-sessions", { form: formData, signal });
export const getSpeakingMock = (id, { signal } = {}) => request("GET", `/speaking/mock-sessions/${id}`, { signal });
export const submitSpeakingMockTurn = (id, formData, { signal } = {}) => request("POST", `/speaking/mock-sessions/${id}/turns`, { form: formData, signal });
export const completeSpeakingMock = (id, { signal } = {}) => request("POST", `/speaking/mock-sessions/${id}/complete`, { signal });
