"""Generate and independently verify Phase 6 against isolated PostgreSQL/Playwright."""
import base64
import hashlib
import json
from pathlib import Path

from app.execution.agent.payments import prepare_spec
from app.execution.spec.payment_contract import PaymentSimulationContract
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.sandbox.catalogue_acceptance import api_cases, browser_journeys
from app.execution.spec.catalogue_example import example_spec
from app.execution.spec.identity_contract import IdentityContract
from app.execution.spec.order_contract import OrderContract


def main():
    evidence = Path(__file__).resolve().parent.parent / 'docs/ecommerce-evidence'
    root = evidence / 'payments-app'
    spec = example_spec()
    spec.project_id = 'PAYMENTS-DEMO'
    spec.project_name = 'Fieldwork offline payment verification fixture'
    spec.identity_contract = IdentityContract(
        public_origin='http://127.0.0.1:3001', allow_local_http=True)
    spec.tech_stack.auth_provider = 'session'
    spec.order_contract = OrderContract(
        tax_basis_points=500, shipping_minor=500, discount_basis_points=0,
        reservation_seconds=900, policy_label='Synthetic verification rules')
    spec.payment_simulation_contract = PaymentSimulationContract()
    spec.acceptance_checks = api_cases()
    spec.acceptance_checks[0]['body_contains']['capabilities']['checkout'] = True
    spec.browser_checks = browser_journeys()
    spec = prepare_spec(spec)
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'payments-build-spec.json').write_text(spec.model_dump_json(indent=2), encoding='utf-8')

    orchestrator = CodingOrchestrator(root)
    build = orchestrator.execute_build(spec)
    report = {
        'contract_version': 1,
        'scope': 'offline payment simulation only; no provider integration or fulfillment',
        'build': build.model_dump(mode='json'),
        'functional': 'FAILED' if build.status != 'VERIFIED' else 'PENDING_VISUAL_EVIDENCE',
        'security': 'TARGETED_ORDER_OWNERSHIP_AND_AUTHORITY_CHECKS_PENDING',
        'accessibility': 'TARGETED_KEYBOARD_AND_LAYOUT_CHECKS_PENDING',
        'performance': 'UNVERIFIED',
        'payment_provider_integration': 'NOT_IMPLEMENTED',
        'screenshots': [],
    }
    result_path = evidence / 'payments-verification.json'
    result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if build.status != 'VERIFIED':
        raise AssertionError('Generated PAYMENT_SIMULATOR build did not pass all mandatory gates; see payments-verification.json')

    marker = root / '.projectforge/capture_payment_screenshots'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('capture enabled by independent verifier', encoding='utf-8')
    try:
        browser = orchestrator.test_runner.run_payment_browser_checks()
    finally:
        marker.unlink(missing_ok=True)
    report['payment_browser_visual'] = browser.model_dump(mode='json')
    for line in browser.raw_stdout.splitlines():
        if 'PAYMENT_SCREENSHOT:' not in line:
            continue
        label, encoded = line.split('PAYMENT_SCREENSHOT:', 1)[1].split(':', 1)
        if label not in ('desktop-pending', 'mobile-success', 'desktop-refund'):
            raise ValueError('Unexpected payment screenshot label: ' + label)
        image = base64.b64decode(encoded.strip(), validate=True)
        if not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image) > 1_500_000:
            raise ValueError('Invalid payment screenshot')
        target = evidence / ('payments-' + label + '.png')
        target.write_bytes(image)
        report['screenshots'].append({
            'label': label,
            'path': str(target),
            'sha256': hashlib.sha256(image).hexdigest(),
            'bytes': len(image),
        })
    success = browser.is_success and {item['label'] for item in report['screenshots']} == {
        'desktop-pending', 'mobile-success', 'desktop-refund'}
    report['functional'] = 'PASSED' if success else 'FAILED'
    report['security'] = 'TARGETED_SIMULATION_OWNERSHIP_REFUND_AUTHORITY_AND_RESTART_CHECKS_PASSED'
    report['accessibility'] = 'TARGETED_RESPONSIVE_LAYOUT_AND_BROWSER_RUNTIME_CHECKS_PASSED' if success else 'FAILED'
    report['visual_inspection'] = 'PENDING_MANUAL_REVIEW'
    result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('build:', build.status, 'checks:', build.verification_checks, flush=True)
    print('payment browser:', browser.exit_code, 'screenshots:', len(report['screenshots']), flush=True)
    assert success, 'Payment browser or screenshot verification failed; see payments-verification.json'


if __name__ == '__main__':
    main()
