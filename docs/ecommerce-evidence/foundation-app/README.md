# Foundation Task Manager

Source compiled from the validated AI-designed specification using DECLARATIVE_CRUD.
This mode supports an unauthenticated single-entity CRUD application. It does not claim arbitrary code synthesis.
Verification results are stored separately; source generation alone does not establish working behavior.

Backend: `cd backend`, install requirements in a virtual environment, then `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.
Frontend: `cd frontend`, `npm install --ignore-scripts`, then `npm run dev` (http://127.0.0.1:3001).
Tests: run `python -m pytest tests` from backend after installing requirements.
Data persists in backend/notes.db; PROJECTFORGE_DATABASE_PATH can select a separate database for testing.
