const MODEL = "@cf/openai/whisper-large-v3-turbo";
const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const MAX_PROMPT_CHARS = 1800;

function bytesToBase64(bytes) {
  const chunkSize = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return btoa(binary);
}

async function tokenMatches(actual, expected) {
  if (!actual || !expected) return false;
  const encoder = new TextEncoder();
  const [actualHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(actual)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  const a = new Uint8Array(actualHash);
  const b = new Uint8Array(expectedHash);
  let difference = a.length ^ b.length;
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    difference |= a[index] ^ b[index];
  }
  return difference === 0;
}

function json(body, status = 200) {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

function decodePrompt(value) {
  if (!value) return "";
  try {
    const bytes = Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
    return new TextDecoder().decode(bytes).slice(0, MAX_PROMPT_CHARS);
  } catch {
    return "";
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ready: true, provider: "cloudflare-workers-ai", model: MODEL });
    }
    if (request.method !== "POST" || url.pathname !== "/transcribe") {
      return json({ error: "Not found" }, 404);
    }

    const authorization = request.headers.get("Authorization") || "";
    const suppliedToken = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
    if (!(await tokenMatches(suppliedToken, env.STT_SHARED_SECRET))) {
      return json({ error: "Unauthorized" }, 401);
    }

    const declaredLength = Number(request.headers.get("Content-Length") || 0);
    if (declaredLength > MAX_AUDIO_BYTES) {
      return json({ error: "Audio exceeds 25 MB" }, 413);
    }
    const audio = new Uint8Array(await request.arrayBuffer());
    if (!audio.length) return json({ error: "Audio body is empty" }, 400);
    if (audio.length > MAX_AUDIO_BYTES) return json({ error: "Audio exceeds 25 MB" }, 413);

    const initialPrompt = decodePrompt(request.headers.get("X-Initial-Prompt-B64"));
    try {
      const result = await env.AI.run(MODEL, {
        audio: bytesToBase64(audio),
        task: "transcribe",
        language: "en",
        vad_filter: true,
        beam_size: 5,
        condition_on_previous_text: false,
        no_speech_threshold: 0.6,
        compression_ratio_threshold: 2.4,
        log_prob_threshold: -1,
        hallucination_silence_threshold: 1.0,
        ...(initialPrompt ? { initial_prompt: initialPrompt } : {}),
      });
      return json({ ...result, model: MODEL });
    } catch (error) {
      console.error("Workers AI transcription failed", error);
      return json({ error: "Transcription failed" }, 502);
    }
  },
};
