import { request } from "../../shared/api/transport.js";

export const listAssignments = (classId) => request("GET", `/classes/${classId}/assignments`);
export const getAssignment = (id) => request("GET", `/assignments/${id}`);
export const getTeacherAssignment = (id) => request("GET", `/teacher/assignments/${id}`, { teacher: true });
export const createAssignment = (formData) => request("POST", "/assignments", { form: formData, teacher: true });
export const updateAssignment = (id, formData) => request("PATCH", `/assignments/${id}`, { form: formData, teacher: true });
export const deleteAssignment = (id) => request("DELETE", `/assignments/${id}`, { teacher: true });
