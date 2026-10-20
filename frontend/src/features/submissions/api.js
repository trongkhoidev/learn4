import { request } from "../../shared/api/transport.js";

export const submit = (assignmentId, formData) => request("POST", `/assignments/${assignmentId}/submit`, { form: formData });
export const listSubmissions = (assignmentId) => request("GET", `/assignments/${assignmentId}/submissions`, { teacher: true });
export const getSubmission = (id) => request("GET", `/submissions/${id}`);
export const patchSubmission = (id, patch) => request("PATCH", `/submissions/${id}`, { json: patch, teacher: true });
export const roster = (classId, name) => request("GET", `/classes/${classId}/roster?name=${encodeURIComponent(name)}`);
