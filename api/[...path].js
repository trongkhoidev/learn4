export const config = {
  runtime: 'edge',
};

export default async function handler(req) {
  const url = new URL(req.url);
  const primaryBackend = (process.env.BACKEND_URL || "https://learn4.onrender.com").replace(/\/+$/, "");
  const fallbackBackend = "https://lexilearn-backend.onrender.com";

  let pathname = url.pathname;
  if (pathname.includes("[...path]")) {
    const matched = req.headers.get("x-matched-path") || req.headers.get("x-invoke-path");
    if (matched) pathname = matched;
  }

  const query = url.search || "";
  const candidateUrls = [
    `${primaryBackend}${pathname}${query}`,
  ];
  if (fallbackBackend !== primaryBackend) {
    candidateUrls.push(`${fallbackBackend}${pathname}${query}`);
  }

  let lastError = null;

  for (const targetUrl of candidateUrls) {
    try {
      const targetHost = new URL(targetUrl).host;
      const headers = new Headers(req.headers);
      headers.set("ngrok-skip-browser-warning", "true");
      headers.set("host", targetHost);

      const options = {
        method: req.method,
        headers: headers,
        signal: AbortSignal.timeout(12000),
      };

      if (req.method !== "GET" && req.method !== "HEAD") {
        options.body = req.body;
        options.duplex = "half";
      }

      const response = await fetch(targetUrl, options);
      if (response.ok || response.status < 500) {
        return response;
      }
      lastError = new Error(`Upstream returned HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
  }

  return new Response(
    JSON.stringify({
      detail: "Máy chủ đang trong quá trình khởi động (Render Cold Start). Vui lòng chờ 30 giây rồi tải lại trang.",
      error: lastError ? lastError.message : "Backend unavailable",
    }),
    {
      status: 503,
      headers: { "Content-Type": "application/json" },
    }
  );
}
