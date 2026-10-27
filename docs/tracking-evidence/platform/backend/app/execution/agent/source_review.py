"""Static checks only: generated Python is parsed, never imported on the host."""
import ast


def same_path(pattern, concrete):
    left, right = pattern.split('/'), concrete.split('/')
    return len(left) == len(right) and all(a == b or (a.startswith('{') and a.endswith('}') and bool(b)) for a, b in zip(left, right))


def review_python(source, path, checks):
    if not path.endswith('/app/main.py'):
        return []
    tree = ast.parse(source)
    errors = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or not fn.decorator_list:
            continue
        for decorator in fn.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute) or not decorator.args:
                continue
            route = decorator.args[0]
            if not isinstance(route, ast.Constant) or not isinstance(route.value, str):
                continue
            expected = {check['status'] for check in checks if check.get('method', '').lower() == decorator.func.attr
                        and same_path(route.value, check.get('path', '')) and 200 <= check.get('status', 0) < 300}
            if len(expected) == 1:
                declared = next((kw.value for kw in decorator.keywords if kw.arg == 'status_code'), ast.Constant(value=200))
                direct = {kw.value.value for node in ast.walk(fn) if isinstance(node, ast.Return) and isinstance(node.value, ast.Call)
                          for kw in node.value.keywords if kw.arg == 'status_code' and isinstance(kw.value, ast.Constant)}
                if isinstance(declared, ast.Constant) and declared.value not in expected and not (expected & direct):
                    errors.append(f'{decorator.func.attr.upper()} {route.value}: declare status_code={next(iter(expected))} or return that explicit Response status.')
            arguments = fn.args.args
            defaults = [None] * (len(arguments) - len(fn.args.defaults)) + list(fn.args.defaults)
            for arg, default in zip(arguments, defaults):
                annotation = arg.annotation
                if isinstance(annotation, ast.Name) and 'session' in annotation.id.lower() and default is None:
                    errors.append(f'{fn.name}: a SQLAlchemy session is not an HTTP parameter. Use Depends(get_db) or open a session inside the function.')
            results = {target.id for node in ast.walk(fn) if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'execute'
                       for target in node.targets if isinstance(target, ast.Name)}
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id in results and node.func.attr in ('update', 'delete', 'commit'):
                        errors.append(f'{fn.name}: SQL Result objects have no {node.func.attr} method. Fetch an ORM instance, modify/delete it through the session, then commit.')
            for name in results:
                count = sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name) and node.func.value.id == name
                            and node.func.attr == 'scalar' for node in ast.walk(fn))
                if count > 1:
                    errors.append(f'{fn.name}: fetch the result once; repeated {name}.scalar() consumes the same result.')
    return list(dict.fromkeys(errors))


def review_json(value, path):
    if path.endswith('tsconfig.json'):
        for entry in value.get('include', []):
            if entry.startswith('frontend/'):
                return ['tsconfig include paths are relative to frontend/: use src or src/**/*.tsx, not frontend/src.']
    return []


def normalize_tsconfig(value):
    # Configuration paths are relative to frontend/, while the manifest uses
    # project-root paths. This conversion preserves the referenced files.
    for key in ('include', 'exclude'):
        if isinstance(value.get(key), list):
            value[key] = [item.removeprefix('frontend/') for item in value[key]]
    options = value.get('compilerOptions', {})
    for key in ('rootDir', 'outDir'):
        if isinstance(options.get(key), str):
            options[key] = options[key].removeprefix('frontend/')
    if isinstance(options.get('types'), list):
        options['types'] = [item.removeprefix('@types/') for item in options['types']]
    return value
