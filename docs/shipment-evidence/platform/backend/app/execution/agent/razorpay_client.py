"""Small test-only Razorpay REST boundary. Never log credentials or raw responses."""
import base64
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


class ProviderUnavailable(RuntimeError):
    pass


class ProviderMismatch(RuntimeError):
    pass


def identifier(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r'_[A-Za-z0-9]{1,80}', value):
        raise ProviderMismatch('Invalid provider identifier')
    return value


def verify_signature(raw, signature, secret):
    if not isinstance(signature, str) or not re.fullmatch(r'[0-9a-f]{64}', signature):
        return False
    return hmac.compare_digest(hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(), signature)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class RazorpayTestClient:
    def __init__(self, key_id, key_secret, webhook_secret, account_id):
        if not re.fullmatch(r'rzp_test_[A-Za-z0-9]+', key_id or ''):
            raise ProviderUnavailable('A Razorpay TEST key is required; live mode is disabled')
        if not key_secret or len(webhook_secret or '') < 16 or not re.fullmatch(r'acc_[A-Za-z0-9]+', account_id or ''):
            raise ProviderUnavailable('Configure the server test secret, webhook secret and account ID')
        self.key_id = key_id
        self._secret = key_secret
        self._webhook_secret = webhook_secret
        self.account_id = account_id

    @classmethod
    def from_environment(cls):
        if os.environ.get('RAZORPAY_TEST_ENABLED') != '1':
            raise ProviderUnavailable('Razorpay test integration is not configured')
        return cls(*(os.environ.get(k, '') for k in ('RAZORPAY_TEST_KEY_ID', 'RAZORPAY_TEST_KEY_SECRET', 'RAZORPAY_TEST_WEBHOOK_SECRET', 'RAZORPAY_TEST_ACCOUNT_ID')))

    def _request(self, method, path, payload=None, headers=None):
        auth = base64.b64encode((self.key_id + ':' + self._secret).encode()).decode()
        request = urllib.request.Request('https://api.razorpay.com/v1/' + path,
            data=json.dumps(payload).encode() if payload is not None else None, method=method,
            headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json', **(headers or {})})
        try:
            # Fixed HTTPS destination, no redirects, bounded response and timeout.
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=8) as response:
                raw = response.read(262145)
            if len(raw) > 262144: raise ValueError('Oversized response')
            value = json.loads(raw)
            if not isinstance(value, dict): raise ValueError('Invalid response')
            return value
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ProviderUnavailable('Provider request failed or outcome is uncertain; reconcile before retrying') from None

    def create_order(self, amount, currency, receipt):
        return self._request('POST', 'orders', {'amount': amount, 'currency': currency, 'receipt': receipt, 'partial_payment': False})

    def find_order(self, receipt):
        result = self._request('GET', 'orders?' + urllib.parse.urlencode({'receipt': receipt, 'count': 100}))
        values = result.get('items', [])
        if not isinstance(values, list): raise ProviderMismatch('Invalid order collection')
        matching = [o for o in values if isinstance(o, dict) and o.get('receipt') == receipt]
        if len(matching) > 1: raise ProviderMismatch('Ambiguous provider receipt')
        return matching[0] if matching else None

    def order(self, oid):
        return self._request('GET', 'orders/' + identifier(oid, 'order'))

    def payments(self, oid):
        result = self._request('GET', 'orders/' + identifier(oid, 'order') + '/payments')
        values = result.get('items')
        if not isinstance(values, list) or len(values) > 100 or any(not isinstance(v,dict) for v in values): raise ProviderMismatch('Invalid payment collection')
        return values

    def payment(self, pid):
        return self._request('GET', 'payments/' + identifier(pid, 'pay'))

    def refund(self, pid, amount, key):
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', key): raise ProviderMismatch('Invalid refund key')
        return self._request('POST', 'payments/' + identifier(pid, 'pay') + '/refund',
                             {'amount': amount, 'speed': 'normal'}, {'X-Refund-Idempotency': key})

    def fetch_refund(self, rid):
        return self._request('GET', 'refunds/' + identifier(rid, 'rfnd'))

    def verify_checkout(self, oid, pid, signature):
        return verify_signature((identifier(oid, 'order') + '|' + identifier(pid, 'pay')).encode(), signature, self._secret)

    def verify_webhook(self, raw, signature):
        return verify_signature(raw, signature, self._webhook_secret)
