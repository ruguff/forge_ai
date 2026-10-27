import base64,json,secrets,subprocess,time,urllib.request
from playwright.sync_api import sync_playwright,expect
ORIGIN='http://127.0.0.1:3001'
def ready(url):
    for _ in range(150):
        try:urllib.request.urlopen(url,timeout=1).close();return
        except Exception:time.sleep(.1)
    raise AssertionError('Preview failed to start: '+url)
def test_simulated_payment_and_admin_refund_browser():
    backend=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-proxy-headers'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frontend=subprocess.Popen(['/opt/frontend/node_modules/.bin/vite','--host','127.0.0.1','--port','3001'],cwd='frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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
            panel=page.get_by_test_id('payment-simulator-1')
            expect(panel).to_contain_text('OFFLINE PAYMENT SIMULATOR')
            panel.get_by_role('button',name='Start simulated payment',exact=True).click()
            expect(panel.get_by_test_id('payment-status')).to_have_text('Simulation: pending')
            capture=__import__('pathlib').Path('/source/.projectforge/capture_payment_screenshots').exists()
            if capture:
                print('PAYMENT_SCREENSHOT:desktop-pending:'+base64.b64encode(page.screenshot(full_page=True,animations='disabled')).decode(),flush=True)
            panel.get_by_role('button',name='Simulate success',exact=True).click()
            expect(panel.get_by_test_id('payment-status')).to_have_text('Simulation: succeeded')
            page.reload()
            panel=page.get_by_test_id('payment-simulator-1')
            expect(panel.get_by_test_id('payment-status')).to_have_text('Simulation: succeeded')
            expect(page.get_by_test_id('order-history')).to_contain_text('simulated_paid')
            assert page.get_by_role('button',name='Start full simulated refund',exact=True).count()==0
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            if capture:
                print('PAYMENT_SCREENSHOT:mobile-success:'+base64.b64encode(page.screenshot(full_page=True,animations='disabled')).decode(),flush=True)
            # Create a second order and use the separate failure action.
            page.goto(ORIGIN+'/products/trail-pack');page.get_by_test_id('order-add').click()
            expect(page.get_by_role('status')).to_contain_text('Added to cart')
            page.goto(ORIGIN+'/cart');page.get_by_test_id('order-checkout').click()
            expect(page.get_by_test_id('order-message')).to_contain_text('Order #2 is awaiting_payment')
            failed=page.get_by_test_id('payment-simulator-2')
            failed.get_by_role('button',name='Start simulated payment',exact=True).click()
            failed.get_by_role('button',name='Simulate failure',exact=True).click()
            expect(failed.get_by_test_id('payment-status')).to_have_text('Simulation: failed')
            # Provision only a synthetic test admin with the operator API, never public signup.
            from app.main import app
            from app.identity_runtime import create_admin
            admin_email='admin-'+email
            create_admin(app.state.engine,app.state.identity_metadata,admin_email,password)
            admin_page=browser.new_page(viewport={'width':1440,'height':1000})
            admin_page.on('pageerror',lambda error:errors.append(str(error)))
            admin_page.goto(ORIGIN+'/account')
            admin_page.get_by_test_id('identity-email').fill(admin_email)
            admin_page.get_by_test_id('identity-password').fill(password)
            admin_page.get_by_test_id('identity-submit').click()
            expect(admin_page.get_by_role('heading',name='Welcome, Administrator')).to_be_visible()
            admin_page.goto(ORIGIN+'/admin/orders')
            admin_panel=admin_page.get_by_test_id('payment-simulator-1')
            admin_panel.get_by_role('button',name='Start full simulated refund',exact=True).click()
            expect(admin_panel.get_by_test_id('payment-status')).to_contain_text('Refund pending')
            admin_panel.get_by_role('button',name='Simulate refund failure',exact=True).click()
            expect(admin_panel).to_contain_text('Refund history: #1 failed')
            admin_panel.get_by_role('button',name='Start full simulated refund',exact=True).click()
            admin_panel.get_by_role('button',name='Simulate refund success',exact=True).click()
            expect(admin_panel.get_by_test_id('payment-status')).to_have_text('Simulation: refunded')
            expect(admin_panel).to_contain_text('#2 succeeded')
            assert admin_page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            if capture:
                print('PAYMENT_SCREENSHOT:desktop-refund:'+base64.b64encode(admin_page.screenshot(full_page=True,animations='disabled')).decode(),flush=True)
            page.goto(ORIGIN+'/orders')
            expect(page.get_by_test_id('payment-simulator-1')).to_contain_text('Simulation: refunded')
            page.goto(ORIGIN+'/admin/orders')
            expect(page.get_by_test_id('order-message')).to_contain_text('Administrator role required')
            assert not errors,errors
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=5);backend.wait(timeout=5)
