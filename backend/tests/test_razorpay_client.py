import hashlib,hmac,json,urllib.error
import pytest
from app.execution.agent.razorpay_client import RazorpayTestClient,ProviderMismatch,ProviderUnavailable,NoRedirect

def client():return RazorpayTestClient('rzp_test_SYNTHETIC','synthetic-secret','synthetic-webhook-secret','acc_SYNTHETIC')

def test_raw_body_hmac_is_exact_and_checkout_uses_saved_order():
    c=client();raw=b'{ "test": true }'
    signature=hmac.new(b'synthetic-webhook-secret',raw,hashlib.sha256).hexdigest()
    assert c.verify_webhook(raw,signature)
    assert not c.verify_webhook(b'{"test":true}',signature)
    assert not c.verify_webhook(raw,'x'*64)
    signature=hmac.new(b'synthetic-secret',b'order_A|pay_B',hashlib.sha256).hexdigest()
    assert c.verify_checkout('order_A','pay_B',signature)
    assert not c.verify_checkout('order_OTHER','pay_B',signature)

def test_environment_opt_in_and_live_key_denial(monkeypatch):
    monkeypatch.delenv('RAZORPAY_TEST_ENABLED',raising=False)
    with pytest.raises(ProviderUnavailable):RazorpayTestClient.from_environment()
    for key in ('rzp_live_BAD','https://hostile.invalid',''):
        with pytest.raises(ProviderUnavailable):RazorpayTestClient(key,'x','synthetic-webhook-secret','acc_A')

def test_fixed_https_refund_header_and_no_redirect(monkeypatch):
    captured=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,size):assert size==262145;return b'{"id":"rfnd_A"}'
    class Opener:
        def open(self,request,timeout):
            assert timeout==8;captured.append(request);return Response()
    def opener(handler):assert isinstance(handler,NoRedirect);return Opener()
    monkeypatch.setattr('urllib.request.build_opener',opener)
    assert client().refund('pay_A',100,'stable_synthetic_key')['id']=='rfnd_A'
    r=captured[0];assert r.full_url=='https://api.razorpay.com/v1/payments/pay_A/refund'
    assert r.get_header('X-refund-idempotency')=='stable_synthetic_key'
    assert json.loads(r.data)=={'amount':100,'speed':'normal'}
    assert NoRedirect().redirect_request(None,None,None,None,None,None) is None
    with pytest.raises(ProviderMismatch):client().payment('../../evil')

@pytest.mark.parametrize('raw',[b'[]',b'not json',b'x'*262145],ids=['array','invalid-json','oversized'])
def test_malformed_bounded_responses_do_not_leak(raw,monkeypatch):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self,size):return raw
    class Opener:
        def open(self,*a,**kw):return Response()
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:Opener())
    with pytest.raises(ProviderUnavailable) as caught:client().order('order_A')
    assert 'synthetic-secret' not in str(caught.value)

def test_ambiguous_receipt_and_malformed_payments_rejected(monkeypatch):
    c=client();monkeypatch.setattr(c,'_request',lambda *a:{'items':[{'receipt':'pf_A'},{'receipt':'pf_A'}]})
    with pytest.raises(ProviderMismatch):c.find_order('pf_A')
    monkeypatch.setattr(c,'_request',lambda *a:{'items':[None]})
    with pytest.raises(ProviderMismatch):c.payments('order_A')
