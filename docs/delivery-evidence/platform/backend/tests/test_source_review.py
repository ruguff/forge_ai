from app.execution.agent.source_review import review_python, review_json


def test_fastapi_dependency_and_mutation_errors_are_rejected_statically():
    source = '''
@app.put('/api/notes/{note_id}')
def update_note(session: Session, note_id: int, note: dict):
    result = session.execute(select(Note))
    result.update(Note.title == note['title'])
    if not result.scalar():
        raise Exception('missing')
    return result.scalar()
@app.post('/api/notes')
def create_note(note: dict):
    return note
@app.delete('/api/notes/{note_id}')
def delete_note(note_id: int):
    return None
'''
    checks = [{'method':'POST','path':'/api/notes','status':201},
              {'method':'DELETE','path':'/api/notes/1','status':204}]
    errors = review_python(source, 'backend/app/main.py', checks)
    assert any('Depends' in error for error in errors)
    assert any('no update' in error for error in errors)
    assert any('repeated' in error for error in errors)
    assert any('status_code=201' in error for error in errors)
    assert any('status_code=204' in error for error in errors)


def test_valid_dependency_and_response_status_are_allowed():
    source = '''
@app.post('/api/notes', status_code=201)
def create_note(note: dict, db: Session = Depends(get_db)):
    return note
@app.delete('/api/notes/{note_id}')
def delete_note(note_id: int):
    return Response(status_code=204)
'''
    assert not review_python(source, 'backend/app/main.py', [
        {'method':'POST','path':'/api/notes','status':201}, {'method':'DELETE','path':'/api/notes/1','status':204}])
    assert review_json({'include':['frontend/src']}, 'frontend/tsconfig.json')
    assert not review_json({'include':['src']}, 'frontend/tsconfig.json')
