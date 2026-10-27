"""Read-only database schema inspection. Run from any working directory."""
import json
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [root / 'backend/data/projects.sqlite3',
         root / 'backend/generated_projects/PROJ-3D627C8F607B/v2/backend/notes.db']
for path in paths:
    print(f'\nDATABASE: {path}')
    if not path.is_file():
        print('Not created yet; start the corresponding application first.')
        continue
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        tables = db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        for name, ddl in tables:
            safe_name = '"' + name.replace('"', '""') + '"'
            print(json.dumps({'table': name, 'sql': ddl,
                'columns': db.execute(f'PRAGMA table_info({safe_name})').fetchall(),
                'foreign_keys': db.execute(f'PRAGMA foreign_key_list({safe_name})').fetchall(),
                'row_count': db.execute(f'SELECT COUNT(*) FROM {safe_name}').fetchone()[0]}, indent=2))
        print('INDEXES:', json.dumps(db.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'").fetchall()))
