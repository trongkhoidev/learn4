# Deploy LexiLearn Backend lên Railway

Tài liệu này hướng dẫn cách đưa FastAPI Backend lên Railway để chạy 24/7 trên Cloud, không cần chạy port 8000 và 4040 (ngrok) trên máy Mac cá nhân.

---

## 1. Tạo Project trên Railway

1. Truy cập [railway.com](https://railway.com) và đăng nhập (bằng tài khoản GitHub).
2. Bấm **New Project** > **Deploy from GitHub repo**.
3. Chọn repo `trongkhoidev/learn4`.
4. Chọn service vừa tạo > vào tab **Settings**:
   - **Root Directory**: nhập `/backend`
   - **Build Command**: để mặc định (Railway sẽ tự động đọc `backend/Dockerfile` hoặc `backend/railway.json`).
5. Vào tab **Networking**:
   - Bấm **Generate Domain** (Railway sẽ cấp một link dạng `https://xxx.up.railway.app`).

---

## 2. Thêm Biến Môi Trường (Variables)

Vào tab **Variables** của service trên Railway, bấm **Raw Editor** và dán toàn bộ nội dung từ file `deploy/railway/env.example`.

Các biến cốt lõi gồm:
- `GROQ_API_KEY`: Key Groq
- `GOOGLE_API_KEY`: Key Gemini
- `LLM_PROVIDER`: `gemini`
- `GEMINI_MODEL`: `gemini-3.5-flash-lite`
- `STT_PROVIDER`: `ensemble`
- `STT_ENSEMBLE_PROVIDERS`: `deepgram,cloudflare`
- `DEEPGRAM_API_KEY`: Key Deepgram
- `CLOUDFLARE_WORKER_URL`: Link Worker Whisper
- `CLOUDFLARE_WORKER_TOKEN`: Token Worker
- `DATABASE_URL`: `sqlite:////app/storage/lexilearn.db`
- `STORAGE_DIR`: `/app/storage`
- `CORS_ORIGINS`: `*`

*(Tùy chọn: Vào tab **Volumes** > bấm **Add Volume** và mount vào đường dẫn `/app/storage` nếu muốn giữ file database và audio lâu dài qua các lần redeploy).*

---

## 3. Cập nhật biến môi trường trên Vercel

Khi Railway deploy thành công và cấp domain (ví dụ `https://learn4-backend.up.railway.app`):

Mở Terminal trên máy và chạy lệnh:
```bash
npx vercel env add BACKEND_URL production
```
Nhập giá trị: `https://learn4-backend.up.railway.app` (link Railway vừa cấp).

Sau đó redeploy lại Vercel:
```bash
npx vercel --prod
```

Hoặc cấu hình trực tiếp trên Web:
Vào [Vercel Dashboard](https://vercel.com) > Project `learn4` > **Settings** > **Environment Variables** > Thêm:
- **Key**: `BACKEND_URL`
- **Value**: `https://learn4-backend.up.railway.app`
- **Environment**: Chọn `Production`, `Preview`, `Development`.

---

## 4. Tắt dịch vụ local trên máy Mac

Sau khi Vercel trỏ tới Railway:
- Bạn có thể tắt vĩnh viễn tiến trình Python port 8000 và ngrok 4040 trên máy.
- Trang web `https://learn4-app.vercel.app/speaking/practice` sẽ tự động hoạt động 24/7 trực tiếp qua Railway.
