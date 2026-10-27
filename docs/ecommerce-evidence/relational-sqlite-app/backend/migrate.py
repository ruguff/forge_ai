from app.relational_runtime import create_app, migrate, make_metadata
import json
from pathlib import Path
app = create_app()
schema = json.loads(Path("app/schema.json").read_text())
migrate(app.state.engine, schema, make_metadata(schema))
print("Migration 0001 applied or already current")
