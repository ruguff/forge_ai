"""Independent rendered simulation journey, extending frozen account/cart setup."""
from app.execution.sandbox.order_browser import SOURCE as ORDER_BROWSER

SOURCE = ORDER_BROWSER.split("            page.get_by_role('button',name='Cancel order #1',exact=True).click()")[0]
SOURCE = SOURCE.replace("def test_customer_cart_checkout_and_order_history():", "def test_simulated_payment_and_admin_refund_browser():")
SOURCE += r'''            panel=page.get_by_test_id('payment-simulator-1')
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
'''
