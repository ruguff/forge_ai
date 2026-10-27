"""Crash-safe generation checkpoints; verification is deliberately never cached."""
import hashlib
import json
from pathlib import Path


class BuildCheckpoint:
    FORMAT = 2

    @staticmethod
    def generator_revision():
        digest = hashlib.sha256()
        root = Path(__file__).resolve().parents[1]
        # Reviewed generators also copy contract validators and consume UI
        # manifests from spec; changes there must invalidate recovered sources.
        sources=list((root/'agent').rglob('*'))+list((root/'spec').rglob('*'))
        for source in sorted(sources):
            if not source.is_file() or '__pycache__' in source.parts or source.suffix not in ('.py','.tsx','.css','.json','.svg'):
                continue
            digest.update(source.relative_to(root).as_posix().encode())
            digest.update(source.read_bytes())
        return digest.hexdigest()

    def __init__(self, root, spec, resume=False):
        self.root = Path(root).resolve()
        self.path = self.root / '.projectforge' / 'generation_checkpoint.json'
        fingerprint = hashlib.sha256(json.dumps({'spec':spec.model_dump(mode='json'), 'generator':self.generator_revision()},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.data = {'format': self.FORMAT, 'spec': fingerprint, 'tasks': {}}
        if resume and self.path.exists():
            try:
                old = json.loads(self.path.read_text(encoding='utf-8'))
                if (isinstance(old, dict) and old.get('format') == self.FORMAT
                        and old.get('spec') == fingerprint and isinstance(old.get('tasks'), dict)):
                    self.data = old
            except (ValueError, OSError):
                pass  # Corrupt checkpoint never grants reuse.
        self.reused = set()

    def hashes(self, task):
        result = {}
        for name in sorted(set(task.files_to_create + task.files_allowed_to_modify)):
            path = self.root / name
            if not path.resolve().is_relative_to(self.root):
                raise ValueError('Checkpoint file escapes workspace')
            current = path
            while current != self.root:
                if current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction()):
                    raise ValueError('Checkpoint links are forbidden')
                current = current.parent
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    def can_reuse(self, task):
        saved = self.data['tasks'].get(task.task_id)
        if not saved or not set(task.dependencies).issubset(self.reused):
            return False
        try:
            valid = bool(saved) and saved == self.hashes(task)
        except (OSError, ValueError):
            return False
        if valid:
            self.reused.add(task.task_id)
        return valid

    def completed(self, task):
        self.data['tasks'][task.task_id] = self.hashes(task)
        self.save()

    def invalidate(self, task_id, tasks):
        affected = {task_id}
        while True:
            expanded = affected | {t.task_id for t in tasks if affected.intersection(t.dependencies)}
            if expanded == affected:
                break
            affected = expanded
        for name in affected:
            self.data['tasks'].pop(name, None)
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, sort_keys=True), encoding='utf-8')
        temporary.replace(self.path)
