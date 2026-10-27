FAKE_SOURCE="import copy,hashlib,hmac\nfrom app.razorpay_client import RazorpayTestClient,ProviderUnavailable\nSECRET='synthetic-checkout-secret'\nWEBHOOK='synthetic-webhook-secret-for-tests'\nclass FakeProvider(RazorpayTestClient):\n    def __init__(self):\n        super().__init__('rzp_test_SYNTHETIC',SECRET,WEBHOOK,'acc_SYNTHETIC')\n        self.orders={};self.pays={};self.refunds={};self.refund_keys={};self.creates=0;self.lost_create=False;self.lost_refund=False;self.refund_calls=[]\n    def _request(self,method,path,payload=None,headers=None):\n        if method=='POST' and path=='orders':\n            self.creates+=1;oid='order_'+str(self.creates)\n            value={'id':oid,'entity':'order','status':'created',**payload};self.orders[oid]=value\n            if self.lost_create:self.lost_create=False;raise ProviderUnavailable('synthetic lost response')\n            return copy.deepcopy(value)\n        if path.startswith('orders?'):\n            from urllib.parse import parse_qs\n            receipt=parse_qs(path.split('?')[1])['receipt'][0]\n            return {'items':[copy.deepcopy(v) for v in self.orders.values() if v['receipt']==receipt]}\n        if method=='GET' and path.startswith('orders/'):\n            oid=path.split('/')[1]\n            if path.endswith('/payments'):return {'items':[copy.deepcopy(v) for v in self.pays.values() if v['order_id']==oid]}\n            return copy.deepcopy(self.orders[oid])\n        if method=='GET' and path.startswith('payments/'):return copy.deepcopy(self.pays[path.split('/')[1]])\n        if method=='POST' and path.endswith('/refund'):\n            pid=path.split('/')[1];key=headers['X-Refund-Idempotency'];self.refund_calls.append((key,copy.deepcopy(payload)))\n            if key not in self.refund_keys:\n                rid='rfnd_'+str(len(self.refunds)+1);self.refund_keys[key]=rid\n                self.refunds[rid]={'entity':'refund','id':rid,'payment_id':pid,'amount':payload['amount'],'currency':'INR','status':'pending'}\n            value=self.refunds[self.refund_keys[key]]\n            if self.lost_refund:self.lost_refund=False;raise ProviderUnavailable('synthetic lost refund response')\n            return copy.deepcopy(value)\n        if method=='GET' and path.startswith('refunds/'):return copy.deepcopy(self.refunds[path.split('/')[1]])\n        raise AssertionError((method,path))\n    def pay(self,oid,status='captured'):\n        pid='pay_'+str(len(self.pays)+1);o=self.orders[oid]\n        self.pays[pid]={'entity':'payment','id':pid,'order_id':oid,'amount':o['amount'],'currency':o['currency'],'status':status,'captured':status=='captured','amount_refunded':0}\n        if status=='captured':o['status']='paid'\n        return pid\ndef sign(raw,secret=SECRET):return hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()\n"
import base64,json,secrets,subprocess,time,urllib.request
from playwright.sync_api import sync_playwright,expect
ORIGIN='http://127.0.0.1:3001'
def ready(url):
    for _ in range(150):
        try:urllib.request.urlopen(url,timeout=1).close();return
        except Exception:time.sleep(.1)
    raise AssertionError('Preview failed to start: '+url)
def test_customer_cart_checkout_and_order_history():
    backend=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-proxy-headers'],stdout=None,stderr=None)
    frontend=subprocess.Popen(['/opt/frontend/node_modules/.bin/vite','--host','127.0.0.1','--port','3001'],cwd='frontend',stdout=None,stderr=None)
    password=secrets.token_urlsafe(20);email='browser-'+secrets.token_hex(5)+'@example.com';errors=[]
    try:
        ready(ORIGIN);ready('http://127.0.0.1:8001/api/store')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(ORIGIN+'/account')
            page.get_by_role('button',name='Create account',exact=True).click()
            page.get_by_label('Email',exact=True).fill(email)
            page.get_by_label('Your name',exact=True).fill('Order journey customer')
            page.get_by_test_id('identity-password').fill(password)
            page.get_by_test_id('identity-submit').click()
            expect(page.get_by_test_id('identity-message')).to_contain_text('Continue to sign in')
            page.get_by_test_id('identity-email').fill(email)
            page.get_by_test_id('identity-password').fill(password)
            page.get_by_test_id('identity-submit').click()
            expect(page.get_by_role('heading',name='Welcome, Order journey customer')).to_be_visible()
            address=page.get_by_test_id('identity-address')
            for label,value in [('Label','Home'),('Full name','Order journey customer'),('Address line 1','1 Test road'),('City','Surat'),('Region','Gujarat'),('Postal code','395001'),('Country code','IN')]:address.get_by_label(label,exact=True).fill(value)
            address.get_by_role('button',name='Save address',exact=True).click()
            expect(address.get_by_text('1 Test road, Surat 395001')).to_be_visible()
            page.goto(ORIGIN+'/products/trail-pack')
            page.get_by_test_id('order-add').click()
            expect(page.get_by_role('status')).to_contain_text('Added to cart')
            page.get_by_role('link',name='Review cart',exact=True).click()
            expect(page.get_by_role('heading',name='Your cart')).to_be_visible()
            expect(page.get_by_text('Server quote')).to_be_visible()
            if __import__('pathlib').Path('/source/.projectforge/capture_order_screenshots').exists():
                print('ORDER_SCREENSHOT:desktop-cart:'+base64.b64encode(page.screenshot(full_page=True,animations='disabled')).decode(),flush=True)
            page.get_by_test_id('order-checkout').click()
            expect(page.get_by_test_id('order-message')).to_contain_text('Order #1 is awaiting_payment')
            expect(page.get_by_test_id('order-history')).to_contain_text('No payment collected')

            page.goto(ORIGIN+'/orders')
            expect(page.get_by_test_id('payment-notice')).to_have_text('RAZORPAY TEST MODE Â· No live payments')
            page.get_by_role('button',name='Open Razorpay test checkout').click()
            expect(page.get_by_role('alert')).to_contain_text('unavailable or unconfigured')
            expect(page.get_by_test_id('payment-status')).to_have_text('Provider status: not_started')
            # Replace only the test server's upstream transport. This file is owned
            # by the platform gate and is absent from generated application source.
            backend.terminate();backend.wait(timeout=5)
            from pathlib import Path
            mock=Path('/tmp/mock_rzp_server.py')
            mock.write_text(FAKE_SOURCE+"\nfrom app.main import app\ngateway=FakeProvider()\noriginal=gateway.create_order\ndef create(*args):\n    value=original(*args)\n    gateway.pay(value['id'])\n    return value\ngateway.create_order=create\napp.state.razorpay_client_factory=lambda:gateway\nimport uvicorn\nuvicorn.run(app,host='127.0.0.1',port=8001,proxy_headers=False)\n")
            backend=subprocess.Popen(['python',str(mock)],stdout=None,stderr=None)
            ready('http://127.0.0.1:8001/api/store')
            import hashlib,hmac
            signature=hmac.new(b'synthetic-checkout-secret',b'order_1|pay_1',hashlib.sha256).hexdigest()
            stub="window.Razorpay=class {constructor(o){this.o=o;}open(){const b=document.createElement('button');b.textContent='Complete mocked checkout';b.onclick=()=>{this.o.handler({razorpay_order_id:this.o.order_id,razorpay_payment_id:'pay_1',razorpay_signature:'"+signature+"'});b.remove();};document.body.appendChild(b);}};"
            page.route('https://checkout.razorpay.com/v1/checkout.js',lambda route:route.fulfill(status=200,content_type='application/javascript',body=stub))
            page.get_by_role('button',name='Open Razorpay test checkout').click()
            page.get_by_role('button',name='Complete mocked checkout').click()
            expect(page.get_by_test_id('payment-status')).to_have_text('Provider status: captured')
            expect(page.get_by_test_id('order-history')).to_contain_text('razorpay_test_paid')
            assert page.get_by_role('button',name='Cancel order #1',exact=True).count()==0
            assert page.get_by_role('button',name='Request or retry full test refund').count()==0
            page.reload()
            expect(page.get_by_test_id('payment-status')).to_have_text('Provider status: captured')
            page.get_by_role('button',name='Refresh provider status').focus()
            page.keyboard.press('Enter')
            expect(page.get_by_role('status')).to_contain_text('Saved provider state refreshed.')
            for label,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                page.set_viewport_size({'width':width,'height':height})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Razorpay page horizontal overflow'
                if Path('/source/.projectforge/capture_payment_screenshots').exists():
                    print('RAZORPAY_SCREENSHOT:'+label+':'+base64.b64encode(page.screenshot(full_page=True,animations='disabled')).decode(),flush=True)
            page.goto(ORIGIN+'/admin/orders')
            expect(page.get_by_test_id('order-message')).to_contain_text('Administrator role required')
            assert not errors,errors
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=5);backend.wait(timeout=5)
