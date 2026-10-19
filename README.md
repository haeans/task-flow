# task-flow

상태 카드형 Task 관리 웹 앱. 설계는 PRD.md, ARCHITECTURE.md, DECISIONS.md를 따른다.
현재는 기본 구조(M0)만 있고 Task 기능, 데이터베이스, 로그인은 없다.

## 구조

- `frontend/` 화면 (React·Vite)
- `backend/` API (FastAPI)

## 실행

터미널 두 개를 연다.

```powershell
# 백엔드 (http://127.0.0.1:8000)
cd backend
uv run uvicorn app.main:app --reload

# 프론트엔드 (http://localhost:5173)
cd frontend
npm install
npm run dev
```

프론트엔드는 `/api` 요청을 백엔드(8000)로 넘긴다. 화면에 "API 연결됨"이 보이면 정상이다.
