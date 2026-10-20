const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "") + "/api/v1";

function teacherHeaders() {
  const code = localStorage.getItem("teacher_code") || "";
  return code ? { "X-Teacher-Code": code } : {};
}

export async function request(method, path, { json, form, teacher, signal } = {}) {
  const headers = {
    "ngrok-skip-browser-warning": "true",
  };
  if (teacher) Object.assign(headers, teacherHeaders());

  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form;
  }

  const response = await fetch(API_BASE + path, { method, headers, body, signal });
  const contentType = response.headers.get("content-type") || "";

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      // Keep the HTTP status as the fallback when the response is not JSON.
    }
    throw new Error(detail);
  }

  if (contentType.includes("text/html")) {
    throw new Error("Máy chủ phản hồi trang web thay vì dữ liệu JSON. Vui lòng tải lại trang.");
  }

  return response.json();
}
