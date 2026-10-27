import ast
import json
import pytest
from app.execution.agent.declarative import file_source, validate_scope
from app.execution.spec.build_spec_models import BuildSpec, DatabaseEntityDef, DatabaseFieldDef, APIEndpointDef


def demo_spec():
    return BuildSpec(project_id='PROJ-DECLARATIVE-TEST',project_name='Task Tracker',generation_mode='MODEL',
        source_generation_strategy='DECLARATIVE_CRUD',database_entities=[DatabaseEntityDef(entity_name='Task',table_name='tasks',fields=[
            DatabaseFieldDef(name='id',data_type='integer',is_primary_key=True),
            DatabaseFieldDef(name='label',data_type='string')])],api_endpoints=[
            APIEndpointDef(endpoint_id='LIST',method='GET',path='/api/tasks',description='List',auth_required=False),
            APIEndpointDef(endpoint_id='CREATE',method='POST',path='/api/tasks',description='Create',auth_required=False),
            APIEndpointDef(endpoint_id='UPDATE',method='PUT',path='/api/tasks/{task_id}',description='Update',auth_required=False),
            APIEndpointDef(endpoint_id='DELETE',method='DELETE',path='/api/tasks/{task_id}',description='Delete',auth_required=False)],
        acceptance_checks=[{'method':'POST','path':'/api/tasks','status':201}, {'method':'DELETE','path':'/api/tasks/1','status':204}])


def test_explicit_ui_contract_does_not_infer_controls_from_test_expectations():
    from app.execution.spec.build_spec_models import UIContract
    spec = demo_spec()
    spec.ui_contract = UIContract(namespace='tasks')
    spec.browser_checks = [{'name': 'create', 'steps': [{'action': 'fill', 'selector': '#invented-selector'}]}]
    source = file_source(spec, 'frontend/src/App.tsx')
    assert 'invented-selector' not in source
    assert '"uiNamespace": "tasks"' in source
    assert 'data-record-id={String(row[config.pk])}' in source
    assert spec.ui_contract.selector('delete', 7) == '[data-testid="tasks-delete"][data-record-id="7"]'
    with pytest.raises(ValueError):
        spec.ui_contract.selector('untrusted"]')


def test_declarative_source_uses_actual_entity_and_routes_without_model_code_claim():
    spec = demo_spec()
    source = file_source(spec,'backend/app/main.py')
    ast.parse(source)
    assert "class Task(Base)" in source
    assert "'/api/tasks'" in source and 'status_code=201' in source
    assert 'compiled from the validated model-designed specification' in source
    assert '/api/notes' not in source
    assert 'Task Tracker' in file_source(spec,'frontend/src/App.tsx')
    package = json.loads(file_source(spec,'frontend/package.json'))
    assert package['scripts']['dev']=='vite'
    assert '@types/react' in package['devDependencies']
    assert "cacheDir:'.vite-cache'" in file_source(spec, 'frontend/vite.config.ts')


def test_declarative_scope_does_not_silently_omit_auth_or_custom_files():
    spec = demo_spec()
    spec.api_endpoints[0].auth_required = True
    with pytest.raises(ValueError,match='authentication'):
        validate_scope(spec)
    spec.api_endpoints[0].auth_required = False
    with pytest.raises(ValueError,match='outside the supported'):
        file_source(spec,'backend/custom_logic.py')


@pytest.mark.parametrize('default', ['', "Student's note", '0'])
def test_database_defaults_are_literals_not_unquoted_sql(default):
    spec = demo_spec()
    spec.database_entities[0].fields[1].default_value = default
    tree = ast.parse(file_source(spec, 'backend/app/main.py'))
    defaults = [keyword.value for node in ast.walk(tree)
                if isinstance(node, ast.Call) for keyword in node.keywords
                if keyword.arg == 'server_default']
    assert len(defaults) == 1
    assert isinstance(defaults[0], ast.Constant)
    assert defaults[0].value == default


def test_row_action_classes_match_declared_browser_controls():
    spec = demo_spec()
    spec.browser_checks = [{'name': 'Edit record', 'steps': [
        {'action': 'click', 'selector': '.task-list .edit-btn:first-child'}]},
        {'name': 'Delete record', 'steps': [
        {'action': 'click', 'selector': '.task-list .delete-btn:first-child'}]}]
    source = file_source(spec, 'frontend/src/App.tsx')
    assert '"edit": "edit-btn"' in source
    assert '"delete": "delete-btn"' in source
    assert '<span><button className={config.classes.edit}' in source
    assert '<span><button className={config.classes.delete}' in source


def test_single_class_controls_keep_edit_and_save_distinct():
    spec = demo_spec()
    spec.browser_checks = [
        {'name': 'Create', 'steps': [{'action': 'click', 'selector': '.create-note-btn'},
         {'action': 'visible', 'selector': '.note-list .note-item:first-child'}]},
        {'name': 'Edit', 'steps': [{'action': 'click', 'selector': '.edit-note-btn'},
         {'action': 'click', 'selector': '.save-edit-btn'}]},
        {'name': 'Delete', 'steps': [{'action': 'click', 'selector': '.delete-note-btn'}]}]
    source = file_source(spec, 'frontend/src/App.tsx')
    for name, value in [('create', 'create-note-btn'), ('edit', 'edit-note-btn'),
                        ('save', 'save-edit-btn'), ('delete', 'delete-note-btn'),
                        ('item', 'note-item')]:
        assert f'"{name}": "{value}"' in source


def test_row_attributes_and_action_labels_use_live_records_not_expected_values():
    spec = demo_spec()
    spec.browser_checks = [
        {'name': 'Create', 'steps': [{'action': 'visible', 'selector': '.task-list .task-item[label="Original"]'}]},
        {'name': 'Edit', 'steps': [{'action': 'click', 'selector': '.edit-task-btn[aria-label="Edit Task 1"]'},
                                 {'action': 'visible', 'selector': '.task-list .task-item[label="Changed"]'}]},
        {'name': 'Delete', 'steps': [{'action': 'click', 'selector': '.delete-task-btn[aria-label="Delete Task 1"]'}]},
    ]
    source = file_source(spec, 'frontend/src/App.tsx')
    config = json.loads(source.split('const config = ', 1)[1].split(';\n', 1)[0])
    assert config['rowAttributes'] == ['label']
    assert config['actionLabels'] == {'edit': ['Edit Task ', ''], 'delete': ['Delete Task ', '']}
    assert 'Original' not in source and 'Changed' not in source
    assert 'String(row[config.pk])' in source
    assert "String(row[name]??'')" in source


def test_unbindable_row_action_label_is_rejected_instead_of_hardcoded():
    spec = demo_spec()
    spec.browser_checks = [{'name': 'Edit', 'steps': [
        {'action': 'click', 'selector': '.edit-task-btn[aria-label="Wrong fixed label"]'}]}]
    with pytest.raises(ValueError, match='record ID'):
        file_source(spec, 'frontend/src/App.tsx')
