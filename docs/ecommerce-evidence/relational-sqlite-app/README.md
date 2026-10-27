# Relational CRUD development application

This is a related-data foundation, not an authenticated store. Bind locally only.
No payment, inventory reservation or commerce permissions are implemented.

Backend: create a virtual environment and install backend/requirements.txt.
From backend set POSTGRES_PASSWORD locally, then docker compose up -d --wait.
This development database uses a persistent named volume and binds only to localhost.
Set DATABASE_URL to postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/DATABASE.
Use USER=projectforge and DATABASE=generated_app with the supplied compose file.
URL-encode special characters in the password. Never commit passwords or .env files.
SQLite builds use sqlite:///development.db. Regenerate an explicitly SQLite spec
for that provider; the runtime refuses silent provider substitution.
From backend run python migrate.py, then python -m uvicorn app.main:app --host 127.0.0.1 --port 8001.
Frontend: from frontend run npm install --ignore-scripts and npm run dev.

Migration 0001 is immutable and checksum-checked. Existing unversioned tables or
changed schemas fail closed; there is no destructive reset or automatic migration.
The initial migration manifest is backend/migrations/0001.json. Runtime uses the
identical schema in app/schema.json. Keep both versioned with source control.
API lists are limited to 100 rows by default (maximum 200) with limit/offset.
The initial UI displays the first page only. Database credentials stay server-side.
