# Cloudflare Workers AI STT

This Worker exposes one protected endpoint backed by
`@cf/openai/whisper-large-v3-turbo`.

```sh
cd deploy/cloudflare-stt
npm install
npx wrangler login
npx wrangler secret put STT_SHARED_SECRET
npx wrangler deploy
curl https://<worker>.workers.dev/health
```

Configure the backend with the resulting origin and the same secret:

```dotenv
CLOUDFLARE_WORKER_URL=https://<worker>.workers.dev
CLOUDFLARE_WORKER_TOKEN=<shared-secret>
STT_PROVIDER=ensemble
STT_ENSEMBLE_PROVIDERS=deepgram,cloudflare
STT_ENSEMBLE_MIN_PROVIDERS=2
```

The Worker accepts raw audio at `POST /transcribe`. It does not persist audio.
