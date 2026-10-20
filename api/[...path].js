export const config = {
  runtime: 'edge',
};

export default async function handler(req) {
  const url = new URL(req.url);
  const backendBase = "https://measureless-trogonoid-marisha.ngrok-free.dev";

  let pathname = url.pathname;
  if (pathname.startsWith("/api/storage/")) {
    pathname = pathname.replace("/api/storage/", "/storage/");
  }

  const targetUrl = `${backendBase}${pathname}${url.search}`;

  const headers = new Headers(req.headers);
  headers.set("ngrok-skip-browser-warning", "true");
  headers.set("host", "measureless-trogonoid-marisha.ngrok-free.dev");

  const options = {
    method: req.method,
    headers: headers,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    options.body = req.body;
    options.duplex = "half";
  }

  try {
    return await fetch(targetUrl, options);
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
