# Database design — ProjectForge AI and generated NoteKeeper

Inspected against source code and existing database schemas on October 15, 2026. This document describes the implemented prototype, with proposed improvements explicitly separated.

## 1. Database technology and scope

ProjectForge AI uses SQLite, an embedded relational database stored in a local file. It does not require a separate database server or an internet connection. The active ProjectForge persistence layer uses Python's built-in sqlite3 library. Its generated NoteKeeper application uses SQLAlchemy ORM with SQLite.

Two independent databases serve different applications:

| Application | Database file | Purpose |
|---|---|---|
| ProjectForge AI platform | `D:\capstone_project\backend\data\projects.sqlite3` | Persist project snapshots, changes to project state, and activity events |
| Generated NoteKeeper website | `D:\capstone_project\backend\generated_projects\PROJ-3D627C8F607B\v2\backend\notes.db` | Persist the notes entered in the generated website |

The ProjectForge path can be overridden through PROJECTFORGE_STATE_DB; its default data/projects.sqlite3 is relative to the backend process's working directory. The documented startup command runs from the backend directory. NoteKeeper's default path is resolved relative to its backend source; PROJECTFORGE_DATABASE_PATH can override it.

LM Studio model weights are separate files and are not database tables. Generated source files and verification artifacts are stored in the project workspace on disk, not as source-file rows in these databases.

## 2. ProjectForge data dictionary

### snapshots — latest persisted state for each project

| Column | SQLite type | Key / constraint | Description |
|---|---|---|---|
| project_id | TEXT | Primary key | Application-generated identifier such as PROJ-3D627C8F607B |
| payload | TEXT | NOT NULL | JSON serialization containing state, context, and spec |

The application supplies a valid, nonempty project ID. The existing DDL uses TEXT PRIMARY KEY without a separate NOT NULL constraint; SQLite PRAGMA consequently reports notnull=0 for this field. Do not describe an explicit NOT NULL database constraint that is not present.

The payload contains the structured project state, user requirements and context, specialist specifications, decisions, execution state, and build specification when available. Requirements and agent outputs are nested JSON data, not individual relational tables.

On save, an existing project snapshot is replaced with its latest serialized state. An unchanged serialized snapshot is not written again. On backend startup, snapshots are loaded and validated using application models. A run recorded as actively understanding, analyzing, or building is marked interrupted in memory; model execution does not automatically resume after a process restart.

### history — saved project-state changes

| Column | SQLite type | Key / constraint | Description |
|---|---|---|---|
| id | INTEGER | Primary key | SQLite-generated row identifier; no explicit AUTOINCREMENT keyword |
| project_id | TEXT | Nullable in current schema | Identifies the project associated with the saved change |
| payload | TEXT | NOT NULL | JSON snapshot of state, context, and specification at that save |

A new history row is inserted when a changed snapshot is saved. Snapshot replacement and history insertion occur within the same database connection transaction. History represents saved changes, not every internal computation. There is no dedicated created_at column or implemented retention/deletion schedule in this table.

### events — persistent execution activity

| Column | SQLite type | Key / constraint | Description |
|---|---|---|---|
| id | INTEGER | Primary key, AUTOINCREMENT | Global sequence number used for ordered event replay |
| project_id | TEXT | NOT NULL | Project associated with the event |
| payload | TEXT | NOT NULL | Serialized event JSON |

The application stores execution events and retrieves them by project ID and sequence number to support activity streaming and reconnection. Replay queries return events with id greater than the supplied sequence, ordered by id, up to 100 per query.

### Internal SQLite table

sqlite_sequence is maintained by SQLite for AUTOINCREMENT bookkeeping, including the events sequence. It is not an application entity and should not be counted as a project feature table.

## 3. Relationships and indexes

Logical relationships are snapshots.project_id to history.project_id (one to many) and snapshots.project_id to events.project_id (one to many). The current schema does not declare foreign-key constraints or cascade deletion. These relationships are maintained by application logic, not enforced by SQLite.

The snapshots primary key has an automatic SQLite index. The explicit composite index events_project covers events(project_id, id), supporting project-filtered sequential event replay. No additional index is declared on history.project_id.

## 4. Generated NoteKeeper data dictionary

### notes — user-created notes

| Column | SQLite type | Key / constraint | Description |
|---|---|---|---|
| id | INTEGER | Primary key, NOT NULL | SQLite-assigned note identifier |
| title | TEXT | NOT NULL, DEFAULT '' | Note title |
| body | TEXT | NOT NULL, DEFAULT '' | Note content |

The current table has no user_id, created_at, updated_at, categories, or foreign keys. It is a single-user demonstration with no login or collaboration. Do not include those fields as implemented features in the SRS.

SQLAlchemy creates the table when the generated backend starts. Each request receives a database session. Successful create, update, and delete operations commit to the local SQLite file; list operations read stored records.

| Operation | HTTP endpoint | Successful result |
|---|---|---|
| Create note | POST /api/notes | 201 with the created note |
| List notes | GET /api/notes | 200 with a JSON array |
| Update note | PUT /api/notes/{note_id} | 200 with the updated note |
| Delete note | DELETE /api/notes/{note_id} | 204 with no response body |

For update/delete of an absent note, the generated backend returns 404. Supplied empty/whitespace text, invalid field names, and an empty request object are rejected by application validation. A current limitation is that the database defaults allow omitted title/body fields to become empty strings; the create validator does not consistently enforce presence of every required field. Strict required-title/body enforcement should be documented as pending until corrected and tested. NOT NULL alone does not reject an empty string.

## 5. Storage, integrity, security, and limits

- Data remains in local SQLite files across normal backend restarts. This does not protect against deleting the file, changing the database path, disk failure, or restoring an older copy.
- JSON payloads are stored as TEXT. Application validation uses Pydantic; the SQLite schema does not include CHECK(json_valid(payload)) constraints.
- Database operations use sqlite3 bound parameters or SQLAlchemy queries. The application should remain the normal path for writing data.
- SQLite access is controlled by local filesystem permissions; no separate database username/password is configured for these files.
- Application-level encryption at rest, role-based database access, automatic backup/restore, retention policies, and database migrations are not implemented in the inspected persistence layer.
- The implementation targets a local student demonstration. Concurrent-write scalability, load capacity, and security-hardening claims require additional testing. Do not claim production-scale support from the existing functional verification.
- Back up databases after stopping the related application, or use SQLite's backup API for a consistent live backup. Avoid copying only the main database file during active writes.

## 6. How to view the databases

Use the supplied read-only schema inspector from any PowerShell directory:

```powershell
D:\capstone_project\.venv\Scripts\python.exe D:\capstone_project\scripts\inspect-databases.py
```

It displays actual tables, CREATE TABLE definitions, columns, foreign keys, row counts, and indexes without modifying either database or displaying stored project content. Row counts change as the project is used.

To browse records visually, open a database file in a SQLite database viewer and use its table/data view, preferably in read-only mode. A .db or .sqlite3 file is binary database storage, not a text document.

Useful read-only SQL queries in such a viewer:

```sql
-- In either database: list tables and their definitions.
SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name;

-- In projects.sqlite3:
SELECT project_id, length(payload) AS payload_characters FROM snapshots;
SELECT id, project_id FROM history ORDER BY id DESC LIMIT 20;
SELECT id, project_id FROM events ORDER BY id DESC LIMIT 20;
PRAGMA table_info(snapshots);
PRAGMA index_list(events);

-- In notes.db:
SELECT id, title, body FROM notes ORDER BY id;
PRAGMA table_info(notes);
```

## 7. Suggested database acceptance tests

These are test cases to execute and record, not a claim that all have passed.

| ID | Procedure | Expected result |
|---|---|---|
| DB-01 | Create a ProjectForge project and inspect snapshots | One current snapshot exists for its project ID |
| DB-02 | Save a changed project state | Current snapshot changes and a history row is added |
| DB-03 | Save exactly the same serialized state again | No additional history row is created |
| DB-04 | Restart ProjectForge after saving | Previously saved project data is available; active runs require recovery |
| DB-05 | Generate events and reconnect with a previous sequence | Later events replay in increasing sequence order for that project |
| DB-06 | Create a note with title and body | A notes row is stored and returned by the list API |
| DB-07 | Edit the note | Existing row values change without creating another note |
| DB-08 | Restart NoteKeeper using the same database path | The saved note remains available |
| DB-09 | Delete the note and restart | Deleted note remains absent |
| DB-10 | Submit blank text, unknown fields, or an empty object | API returns 422; no invalid row is inserted |
| DB-11 | Submit only title or only body on create | Desired SRS result: 422; current default/validation gap must be resolved before claiming compliance |
| DB-12 | Update or delete an unknown note ID | API returns 404 |

## 8. Implementation references and scope caution

Active platform persistence: backend/app/api/persistence.py, instantiated by backend/app/api/endpoints.py.

Generated NoteKeeper ORM and routes: backend/generated_projects/PROJ-3D627C8F607B/v2/backend/app/main.py.

An older SQLAlchemy ProjectRecord definition exists in backend/app/models/db_models.py with a projects table. The current FastAPI entry point and project routes use ProjectPersistence instead. Inspection of the active database found no projects table. Describe that ORM definition as unused scaffolding, not as an active table.

The four declared verification checks for the generated project previously passed. This does not establish that every proposed test in this document has been executed, or that the full system has been demonstrated with the laptop's internet disconnected.
