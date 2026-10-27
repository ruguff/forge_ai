from types import SimpleNamespace
from app.execution.spec.build_spec_models import BuildSpec
from app.execution.state.build_checkpoint import BuildCheckpoint


def task(name, dependencies=()):
    return SimpleNamespace(task_id=name, files_to_create=[name + '.txt'],
                           files_allowed_to_modify=[], dependencies=list(dependencies))


def test_resume_checks_spec_files_and_dependency_chain(tmp_path):
    spec = BuildSpec(project_id='test', project_name='test')
    a, b = task('a'), task('b', ['a'])
    for t in (a, b):
        (tmp_path / (t.task_id + '.txt')).write_text('original')
    first = BuildCheckpoint(tmp_path, spec)
    first.completed(a)
    first.completed(b)
    recovered = BuildCheckpoint(tmp_path, spec, resume=True)
    assert not recovered.can_reuse(b)
    assert recovered.can_reuse(a)
    assert recovered.can_reuse(b)
    (tmp_path / 'a.txt').write_text('changed')
    changed = BuildCheckpoint(tmp_path, spec, resume=True)
    assert not changed.can_reuse(a)
    assert not changed.can_reuse(b)
    spec.version += 1
    assert not BuildCheckpoint(tmp_path, spec, resume=True).can_reuse(b)


def test_recovery_is_explicit_and_corruption_safe(tmp_path):
    spec = BuildSpec(project_id='test', project_name='test')
    a = task('a')
    (tmp_path / 'a.txt').write_text('ok')
    checkpoint = BuildCheckpoint(tmp_path, spec)
    checkpoint.completed(a)
    assert not BuildCheckpoint(tmp_path, spec).can_reuse(a)
    checkpoint.path.write_text('{bad json')
    assert not BuildCheckpoint(tmp_path, spec, resume=True).can_reuse(a)


def test_missing_output_cannot_be_checkpointed(tmp_path):
    import pytest
    checkpoint = BuildCheckpoint(tmp_path, BuildSpec(project_id='t', project_name='t'))
    with pytest.raises(FileNotFoundError):
        checkpoint.completed(task('missing'))


def test_generator_changes_invalidate_source_reuse(tmp_path, monkeypatch):
    spec = BuildSpec(project_id='test', project_name='test')
    a = task('a')
    (tmp_path/'a.txt').write_text('old generator output')
    BuildCheckpoint(tmp_path,spec).completed(a)
    monkeypatch.setattr(BuildCheckpoint,'generator_revision',staticmethod(lambda:'different implementation'))
    assert not BuildCheckpoint(tmp_path,spec,resume=True).can_reuse(a)


def test_interruption_after_upstream_rebuild_invalidates_downstream(tmp_path):
    spec = BuildSpec(project_id='t', project_name='t')
    a, b = task('a'), task('b', ['a'])
    for t in (a, b):
        (tmp_path / (t.task_id + '.txt')).write_text('old')
    checkpoint = BuildCheckpoint(tmp_path, spec)
    checkpoint.completed(a)
    checkpoint.completed(b)
    checkpoint.invalidate('a', [a, b])
    (tmp_path / 'a.txt').write_text('new')
    checkpoint.completed(a)
    resumed = BuildCheckpoint(tmp_path, spec, resume=True)
    assert resumed.can_reuse(a)
    assert not resumed.can_reuse(b)
