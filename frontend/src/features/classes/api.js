import { request } from "../../shared/api/transport.js";

export const createClass = (name, teacherNote, level) =>
  request("POST", "/classes", { json: { name, teacher_note: teacherNote, level }, teacher: true });
export const listClasses = () => request("GET", "/classes", { teacher: true });
export const getClass = (id) => request("GET", `/classes/${id}`);
export const join = (code) => request("GET", `/join?code=${encodeURIComponent(code)}`);
export const updateClass = (id, json) => request("PATCH", `/classes/${id}`, { json, teacher: true });
export const deleteClass = (id) => request("DELETE", `/classes/${id}`, { teacher: true });
