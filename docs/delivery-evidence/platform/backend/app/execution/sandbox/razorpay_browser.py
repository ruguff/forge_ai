"""Rendered local test mode, with explicit mocked Checkout; no provider evidence."""
from app.execution.sandbox.order_browser import SOURCE as ORDER_SOURCE
from app.execution.sandbox.razorpay_gate import FAKE

SOURCE = ORDER_SOURCE.split("            page.get_by_role('button',name='Cancel order #1'")[0] + '''
            page.goto(ORIGIN+'/orders')
            expect(page.get_by_test_id('payment-notice')).to_have_text('RAZORPAY TEST MODE · No live payments')
            page.get_by_role('button',name='Open Razorpay test checkout').click()
            expect(page.get_by_role('alert')).to_contain_text('unavailable or unconfigured')
            expect(page.get_by_test_id('payment-status')).to_have_text('Provider status: not_started')
            # Replace only the test server's upstream transport. This file is owned
            # by the platform gate and is absent from generated application source.
            backend.terminate();backend.wait(timeout=5)
            from pathlib import Path
            mock=Path('/tmp/mock_rzp_server.py')
            mock.write_text(FAKE_SOURCE+"\\nfrom app.main import app\\ngateway=FakeProvider()\\noriginal=gateway.create_order\\ndef create(*args):\\n    value=original(*args)\\n    gateway.pay(value['id'])\\n    return value\\ngateway.create_order=create\\napp.state.razorpay_client_factory=lambda:gateway\\nimport uvicorn\\nuvicorn.run(app,host='127.0.0.1',port=8001,proxy_headers=False)\\n")
            backend=subprocess.Popen(['python',str(mock)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
'''
SOURCE = 'FAKE_SOURCE='+repr(FAKE)+'\n'+SOURCE
