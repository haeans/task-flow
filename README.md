# task-flow

상태 카드형 Task 관리 웹 앱. 설계는 PRD.md, ARCHITECTURE.md, DECISIONS.md를 따른다.
카드 등록·상태 변경·수정·삭제를 지원한다. 로그인은 없다.

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

프론트엔드는 `/api` 요청을 백엔드(8000)로 넘긴다. 데이터는 `backend/data/tasks.db`에 저장된다(Git 제외).

## 테스트

```powershell
cd backend
uv run pytest
```
