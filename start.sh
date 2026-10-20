#!/bin/bash

# Dừng script khi có lỗi
set -e

# Chuyển về thư mục chứa script
cd "$(dirname "$0")"

echo "=== LexiLearn Local Development Environment ==="

# 1. Kiểm tra và tạo .env
if [ ! -f .env ]; then
    echo "Tạo file .env từ .env.example..."
    cp .env.example .env
fi

# 2. Cài đặt và khởi chạy Backend
echo "=== Đang thiết lập Backend ==="
cd backend

# Tạo virtual environment nếu chưa có
if [ ! -d ".venv" ]; then
    echo "Tạo Python virtual environment..."
    python3 -m venv .venv
fi

# Kích hoạt venv
source .venv/bin/activate

# Cài đặt requirements
echo "Cài đặt Python dependencies..."
pip install -r requirements.txt

# Chạy backend ở chế độ background
echo "Khởi chạy Backend (Uvicorn)..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

cd ..

# 3. Cài đặt và khởi chạy Frontend
echo "=== Đang thiết lập Frontend ==="
cd frontend

# Cài đặt node_modules nếu chưa có
if [ ! -d "node_modules" ]; then
    echo "Cài đặt Node modules..."
    npm install
fi

# Chạy frontend ở chế độ background
echo "Khởi chạy Frontend (Vite)..."
npm run dev &
FRONTEND_PID=$!

cd ..

echo "=== Đã khởi chạy thành công ==="
echo "Frontend: http://localhost:5173"
echo "Backend: http://localhost:8000"
echo "Nhấn Ctrl+C để dừng cả Frontend và Backend"

# Hàm bắt sự kiện Ctrl+C (SIGINT)
cleanup() {
    echo "Đang dừng Frontend (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID
    echo "Đang dừng Backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID
    echo "Đã dừng hoàn toàn."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Chờ tiến trình
wait $BACKEND_PID $FRONTEND_PID
