import pytest
from pydantic import ValidationError
from app.execution.spec.commerce_contract import CommerceContract, PaymentIntegration
from app.execution.spec.build_spec_models import BuildSpec
from app.execution.agent.declarative import validate_scope


def test_live_payments_and_unknown_payment_options_are_rejected():
    with pytest.raises(ValidationError):
        PaymentIntegration(live_enabled=True)
    with pytest.raises(ValidationError):
        PaymentIntegration(provider='razorpay_live')
    with pytest.raises(ValidationError):
        PaymentIntegration(api_secret='must not appear in specs')


def test_migrations_are_versioned_and_ordered():
    contract = CommerceContract(migrations=[{'revision':'001', 'description':'Initial'},
        {'revision':'002', 'parent':'001', 'description':'Next'}])
    assert contract.migrations[-1].parent == '001'
    with pytest.raises(ValidationError):
        CommerceContract(migrations=[{'revision':'002', 'parent':'missing', 'description':'Invalid'}])


def test_contract_roundtrip_and_unsupported_execution_are_explicit():
    spec = BuildSpec(project_id='commerce', project_name='Store', commerce_contract=CommerceContract())
    assert BuildSpec.model_validate_json(spec.model_dump_json()).commerce_contract.database == 'postgresql'
    with pytest.raises(ValueError, match='cannot be silently omitted'):
        validate_scope(spec)
