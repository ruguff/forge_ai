"""Version 1 independent acceptance fixture for the Fieldwork sample catalogue.

Expected values are platform-owned and are never fed into source generation.
Corrections require a documented contract version change, not a silent rewrite.
"""
from app.execution.spec.catalogue_ui import CatalogueUIContract

CONTRACT_VERSION = 1


def api_cases():
    return [dict(case,requirements=['CAT-001']) for case in [
        {'method':'GET','path':'/api/store','status':200,'body_contains':{'name':'fieldwork','currency':'INR','capabilities':{'checkout':False,'payments':False}}},
        {'method':'GET','path':'/api/categories','status':200,'body_contains':[{'slug':'carry','count':3},{'slug':'camp','count':2}]},
        {'method':'GET','path':'/api/products?limit=6','status':200,'body_contains':{'total':8,'items':[{'slug':'trail-pack','price_minor':249900,'currency':'INR','available':True}]}},
        {'method':'GET','path':'/api/products?q=PACK-OLIVE-18','status':200,'body_contains':{'total':1,'items':[{'slug':'trail-pack'}]}},
        {'method':'GET','path':'/api/products?category=carry','status':200,'body_contains':{'total':3}},
        {'method':'GET','path':'/api/products?in_stock=true','status':200,'body_contains':{'total':7}},
        {'method':'GET','path':'/api/products?min_price=250000&max_price=260000&in_stock=true','status':200,'body_contains':{'total':0}},
        {'method':'GET','path':'/api/products?sort=price-asc&limit=1','status':200,'body_contains':{'items':[{'slug':'market-tote','price_minor':89900}]}},
        {'method':'GET','path':'/api/products?page=2&limit=6','status':200,'body_contains':{'total':8,'items':[{'slug':'daily-pack'},{'slug':'small-bottle'}]}},
        {'method':'GET','path':'/api/products?q=%25','status':200,'body_contains':{'total':0}},
        {'method':'GET','path':'/api/products/trail-pack','status':200,'body_contains':{'slug':'trail-pack','variants':[{'sku':'PACK-OLIVE-18','price_minor':249900,'available':True},{'sku':'PACK-SAND-18','price_minor':259900,'available':False}],'images':[{'url':'/assets/pack-detail.svg'}]}},
        {'method':'GET','path':'/api/products/missing-product','status':404},
        {'method':'GET','path':'/api/products?min_price=3&max_price=1','status':422},
        {'method':'GET','path':'/api/products?limit=49','status':422},
        {'method':'POST','path':'/api/products','json':{'name':'Injected'},'status':405},
    ]]


def browser_journeys():
    ui=CatalogueUIContract().selector
    return [{'name':'Catalogue and variant details','requirements':['CAT-001'],'steps':[
        {'action':'text','selector':ui('results'),'value':'8 essentials'},
        {'action':'click','selector':ui('product','trail-pack')+' a'},
        {'action':'text','selector':ui('sku'),'value':'PACK-OLIVE-18'},
        {'action':'select','selector':ui('variant'),'value':'PACK-SAND-18'},
        {'action':'text','selector':ui('sku'),'value':'PACK-SAND-18'},
        {'action':'text','selector':ui('availability'),'value':'Out of stock'},
        {'action':'click','selector':ui('back')},
        {'action':'fill','selector':ui('search'),'value':'bottle'},
        {'action':'press','selector':ui('search'),'value':'Enter'},
        {'action':'text','selector':ui('results'),'value':'2 essentials'},
    ]}]


POSTGRES_TEST = '''import json
import subprocess
import time
import httpx
import pytest
from sqlalchemy import select,update
from sqlalchemy.exc import IntegrityError
from app.main import app

def start():
    process=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'])
    for _ in range(100):
        try:
            if httpx.get('http://127.0.0.1:8001/api/store').status_code==200:return process
        except httpx.HTTPError:pass
        if process.poll() is not None:raise AssertionError('Backend failed to start')
        time.sleep(.1)
    process.terminate();process.wait(timeout=5)
    raise AssertionError('Backend readiness timeout')

def test_catalogue_postgresql_constraints_visibility_and_restart():
    assert app.state.engine.dialect.name=='postgresql'
    process=start()
    try:
        variants=app.state.metadata.tables['variants']
        products=app.state.metadata.tables['products']
        categories=app.state.metadata.tables['categories']
        images=app.state.metadata.tables['product_images']
        for change in ({'price_minor':-1},{'stock_quantity':-1},{'currency':'USD'},{'sku':'BOTTLE-CLAY-750'},{'product_id':999999}):
            with pytest.raises(IntegrityError),app.state.engine.begin() as conn:
                conn.execute(update(variants).where(variants.c.sku=='PACK-OLIVE-18').values(**change))
        with pytest.raises(IntegrityError),app.state.engine.begin() as conn:
            conn.execute(update(images).values(asset='https://untrusted.invalid/image.svg'))
        with app.state.engine.begin() as conn:
            conn.execute(update(variants).where(variants.c.sku=='PACK-OLIVE-18').values(price_minor=239900,stock_quantity=0))
            conn.execute(update(products).where(products.c.slug=='daily-pack').values(active=False))
            conn.execute(update(categories).where(categories.c.slug=='home').values(active=False))
        with httpx.Client(base_url='http://127.0.0.1:8001') as client:
            assert client.get('/api/products/daily-pack').status_code==404
            assert client.get('/api/products/woven-throw').status_code==404
            assert client.get('/api/products?category=home').json()['total']==0
            assert client.post('/api/products',json={'price_minor':1}).status_code==405
    finally:
        process.terminate();process.wait(timeout=5)
    process=start()
    try:
        with httpx.Client(base_url='http://127.0.0.1:8001') as client:
            row=client.get('/api/products/trail-pack').json()['variants'][0]
            assert row['price_minor']==239900 and row['available'] is False
            assert client.get('/api/products').json()['total']==6
            assert client.get('/api/products/daily-pack').status_code==404
    finally:
        process.terminate();process.wait(timeout=5)
'''


RENDERED_TEST = '''import base64
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

IDS=json.loads(Path('/tmp/workspace/frontend/src/ui-contract.json').read_text())['ids']
def locator(page,name):return page.get_by_test_id(IDS[name])
def ready(url):
    for _ in range(100):
        try:
            urllib.request.urlopen(url,timeout=1).close();return
        except Exception:time.sleep(.1)
    raise AssertionError('Preview did not start')
def snapshot(page,name):
    png=page.screenshot(full_page=True,animations='disabled')
    print('CATALOGUE_SCREENSHOT:'+name+':'+base64.b64encode(png).decode(),flush=True)
def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'),'Horizontal page overflow'
def test_desktop_mobile_keyboard_and_states():
    backend=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frontend=subprocess.Popen(['/opt/frontend/node_modules/.bin/vite','--host','127.0.0.1','--port','3001'],cwd='frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        ready('http://127.0.0.1:8001/api/store');ready('http://127.0.0.1:3001')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            errors=[]
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:3001')
            expect(locator(page,'product')).to_have_count(6)
            expect(locator(page,'results')).to_contain_text('8 essentials')
            page.wait_for_function('Array.from(document.images).every(i => i.complete)')
            no_overflow(page)
            assert page.locator('main').count()==1 and page.locator('h1').count()==1
            assert page.locator('.skip-link').evaluate("e => getComputedStyle(e).clipPath")!='none'
            page.keyboard.press('Tab');expect(page.get_by_text('Skip to main content')).to_be_focused()
            assert page.locator('.skip-link').evaluate("e => getComputedStyle(e).clipPath")=='none'
            page.keyboard.press('Enter');expect(page.locator('#main')).to_be_focused()
            assert page.locator('.skip-link').evaluate("e => getComputedStyle(e).clipPath")!='none'
            snapshot(page,'desktop-catalogue')
            pending=[]
            page.route('**/api/products?**',lambda route:pending.append(route))
            locator(page,'search').fill('bottle');locator(page,'search').press('Enter')
            for _ in range(200):
                if pending:break
                page.wait_for_timeout(10)
            assert pending,'Expected an actual intercepted product request'
            expect(locator(page,'loading')).to_be_visible()
            for route in pending:route.continue_()
            page.unroute('**/api/products?**')
            expect(locator(page,'product')).to_have_count(2)
            locator(page,'search').fill('trail');locator(page,'search').press('Enter')
            expect(locator(page,'product')).to_have_count(1)
            expect(locator(page,'product')).to_contain_text('The trail pack')
            locator(page,'search').fill('no-such-product');locator(page,'search').press('Enter')
            expect(locator(page,'empty')).to_be_visible()
            expect(locator(page,'product')).to_have_count(0)
            page.get_by_role('button',name='Clear search and filters').click()
            expect(locator(page,'product')).to_have_count(6)
            locator(page,'sort').select_option('price-asc')
            expect(locator(page,'product').first).to_contain_text('The market tote')
            locator(page,'clear').click()
            locator(page,'next').click()
            expect(locator(page,'product')).to_have_count(2)
            expect(locator(page,'product').first).to_contain_text('The daily pack')
            locator(page,'previous').click();expect(locator(page,'product')).to_have_count(6)
            # Failure and loading states use intercepted transport, never fake API success.
            page.route('**/api/products?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{}'))
            locator(page,'search').fill('fail');locator(page,'search').press('Enter')
            expect(locator(page,'error')).to_be_visible()
            page.unroute('**/api/products?**')
            locator(page,'retry').click();expect(locator(page,'empty')).to_be_visible()
            locator(page,'clear').click();expect(locator(page,'product')).to_have_count(6)
            for width,height in ((1024,768),(390,844),(320,740)):
                page.set_viewport_size({'width':width,'height':height})
                no_overflow(page)
                if width==390:
                    snapshot(page,'mobile-catalogue')
            page.set_viewport_size({'width':390,'height':844})
            page.get_by_role('button',name='Filters',exact=True).click()
            locator(page,'category').select_option('camp')
            locator(page,'stock').check();locator(page,'apply').click()
            expect(locator(page,'product')).to_have_count(1)
            expect(locator(page,'product')).to_contain_text('The folding stool')
            locator(page,'min-price').fill('30');locator(page,'max-price').fill('10');locator(page,'apply').click()
            expect(locator(page,'error')).to_contain_text('valid price range')
            page.get_by_role('button',name='Reset',exact=True).click()
            expect(locator(page,'product')).to_have_count(6)
            locator(page,'product').filter(has=page.get_by_role('heading',name='The trail pack')).get_by_role('link').click()
            expect(locator(page,'sku')).to_have_text('PACK-OLIVE-18')
            locator(page,'variant').focus();locator(page,'variant').press('ArrowDown');locator(page,'variant').press('Enter')
            expect(locator(page,'sku')).to_have_text('PACK-SAND-18')
            expect(locator(page,'availability')).to_have_text('Out of stock')
            expect(locator(page,'price')).to_contain_text('2,599')
            page.get_by_role('button',name='View image 2').click()
            expect(page.get_by_role('button',name='View image 2')).to_have_attribute('aria-pressed','true')
            no_overflow(page);snapshot(page,'mobile-detail')
            assert page.locator('img:not([alt])').count()==0
            page.route('**/assets/pack-detail.svg',lambda route:route.fulfill(status=404,body=''))
            page.reload()
            expect(locator(page,'sku')).to_have_text('PACK-OLIVE-18')
            page.get_by_role('button',name='View image 2').click()
            expect(page.locator('.detail-image').get_by_role('img',name='Product image unavailable')).to_be_visible()
            page.unroute('**/assets/pack-detail.svg')
            page.goto('http://127.0.0.1:3001/products/%ZZ')
            expect(locator(page,'error')).to_contain_text('not available')
            assert not errors,errors
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=5);backend.wait(timeout=5)
'''
