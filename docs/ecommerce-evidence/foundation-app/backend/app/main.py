# Trusted runtime scaffolding; CRUD implementation compiled from the validated model-designed specification.
from pathlib import Path
from datetime import datetime
import os
from fastapi import FastAPI, Body, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI()
database_path = os.environ.get('PROJECTFORGE_DATABASE_PATH', str(Path(__file__).resolve().parents[1] / 'notes.db'))
engine = create_engine('sqlite:///' + database_path, connect_args={'check_same_thread': False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, nullable=False, unique=False)
    title = Column(String, primary_key=False, nullable=False, unique=False)
    description = Column(Text, primary_key=False, nullable=False, unique=False)

Base.metadata.create_all(engine)

def _get_db():
    with SessionLocal() as db:
        yield db

def _serialize(value):
    if isinstance(value, Base):
        return {column.name: getattr(value, column.name) for column in value.__table__.columns}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value

def _validate_payload(payload, Model, partial=False):
    fields = {column.name: column for column in Model.__table__.columns if not column.primary_key}
    if not payload or set(payload) - set(fields):
        raise HTTPException(422, 'Provide valid fields for this operation')
    for name, column in fields.items():
        if name not in payload:
            if not partial and not column.nullable and column.default is None and column.server_default is None:
                raise HTTPException(422, f'{name} is required')
            continue
        value = payload[name]
        if value is None and not column.nullable:
            raise HTTPException(422, f'{name} is required')
        if isinstance(column.type, (String, Text)) and (not isinstance(value, str) or not value.strip()):
            raise HTTPException(422, f'{name} must be a nonempty string')
        if isinstance(column.type, DateTime) and isinstance(value, str):
            try:
                payload[name] = datetime.fromisoformat(value)
            except ValueError:
                raise HTTPException(422, f'{name} must be an ISO datetime')

def _operation_0(db, payload, Model):
    item_id = None
    return db.query(Model).all()

def _operation_1(db, payload, Model):
    item_id = None
    row = Model(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def _operation_2(db, payload, Model, task_id):
    item_id = task_id
    row = db.get(Model, item_id)
    if row is None:
        raise HTTPException(404, "Not found")
    for name, value in payload.items():
        setattr(row, name, value)
    db.commit()
    db.refresh(row)
    return row

def _operation_3(db, payload, Model, task_id):
    item_id = task_id
    row = db.get(Model, item_id)
    if row is None:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    return None

@app.get('/api/tasks', status_code=200)
def endpoint_0(db: Session = Depends(_get_db)):
    return _serialize(_operation_0(db, None, Task))

@app.post('/api/tasks', status_code=201)
def endpoint_1(payload: dict = Body(...), db: Session = Depends(_get_db)):
    _validate_payload(payload, Task, partial=False)
    return _serialize(_operation_1(db, payload, Task))

@app.put('/api/tasks/{task_id}', status_code=200)
def endpoint_2(task_id: int, payload: dict = Body(...), db: Session = Depends(_get_db)):
    _validate_payload(payload, Task, partial=True)
    return _serialize(_operation_2(db, payload, Task, task_id))

@app.delete('/api/tasks/{task_id}', status_code=204)
def endpoint_3(task_id: int, db: Session = Depends(_get_db)):
    return _serialize(_operation_3(db, None, Task, task_id))
