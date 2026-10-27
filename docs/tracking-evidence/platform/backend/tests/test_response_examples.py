import pytest
from app.execution.spec.model_compiler import contains_response_schema


@pytest.mark.parametrize('value', [
    {'type': 'object', 'properties': {'title': {'type': 'string'}}},
    [{'type': 'object', 'properties': {'id': {'type': 'integer'}}}],
    {'result': {'type': 'array', 'items': {'type': 'string'}}},
])
def test_schema_is_not_an_expected_response_example(value):
    assert contains_response_schema(value)


@pytest.mark.parametrize('value', [
    {'title': 'Test Note', 'body': 'Hello'},
    [{'id': 1, 'title': 'Updated Title'}],
    {'type': 'personal', 'properties': 'plain text'},
    None,
])
def test_real_response_examples_are_preserved(value):
    assert not contains_response_schema(value)
