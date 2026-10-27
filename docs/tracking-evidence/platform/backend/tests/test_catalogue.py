import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.execution.agent.catalogue import prepare_spec,sources
from app.execution.agent.catalogue_runtime import create_app
from app.execution.spec.catalogue_contract import CatalogueContract
from app.execution.spec.catalogue_example import example_spec
from app.execution.spec.catalogue_ui import CatalogueUIContract


@pytest.fixture
def catalogue(tmp_path):
    config=tmp_path/'catalogue.json'
    config.write_text(example_spec().catalogue_contract.model_dump_json(),encoding='utf-8')
    app=create_app(config,'sqlite:///'+str(tmp_path/'catalogue.db'))
    with TestClient(app) as client:
        yield app,client,config,tmp_path


def test_read_only_catalogue_search_filters_and_pagination(catalogue):
    app,client,_,_=catalogue
    result=client.get('/api/products').json()
    assert result['total']==8
    assert all(type(p['price_minor']) is int and p['currency']=='INR' for p in result['items'])
    assert client.get('/api/products?q=PACK-OLIVE-18').json()['items'][0]['slug']=='trail-pack'
    assert client.get('/api/products?category=carry').json()['total']==3
    assert client.get('/api/products?in_stock=true').json()['total']==7
    assert client.get('/api/products?min_price=250000&max_price=260000&in_stock=true').json()['total']==0
    assert client.get('/api/products?min_price=250000&max_price=260000').json()['items'][0]['slug']=='trail-pack'
    prices=[p['price_minor'] for p in client.get('/api/products?sort=price-asc').json()['items']]
    assert prices==sorted(prices)
    first=client.get('/api/products?limit=3&page=1').json()
    second=client.get('/api/products?limit=3&page=2').json()
    assert len(first['items'])==len(second['items'])==3
    assert not {p['id'] for p in first['items']}&{p['id'] for p in second['items']}
    assert client.get('/api/products?category=missing').json()['total']==0
    assert client.post('/api/products',json={'name':'Injected'}).status_code==405
    assert client.delete('/api/products/trail-pack').status_code==405


@pytest.mark.parametrize('query',['q=%25','q=_',"q=%27%20OR%201%3D1--"])
def test_literal_search_characters_do_not_expand_catalogue(catalogue,query):
    assert catalogue[1].get('/api/products?'+query).json()['total']==0


@pytest.mark.parametrize('query',['min_price=3&max_price=1','min_price=-1','limit=49','page=0','sort=DROP','in_stock=maybe'])
def test_invalid_filters_are_rejected(catalogue,query):
    assert catalogue[1].get('/api/products?'+query).status_code==422


def test_variants_gallery_visibility_and_real_stock(catalogue):
    app,client,_,_=catalogue
    detail=client.get('/api/products/trail-pack').json()
    assert len(detail['images'])==2
    assert detail['images'][1]['url']=='/assets/pack-detail.svg'
    assert detail['variants'][0]['sku']=='PACK-OLIVE-18'
    assert detail['variants'][0]['available'] is True
    assert detail['variants'][1]['available'] is False
    assert all('stock_quantity' not in v for v in detail['variants'])
    products=app.state.metadata.tables['products']
    variants=app.state.metadata.tables['variants']
    categories=app.state.metadata.tables['categories']
    with app.state.engine.begin() as conn:
        conn.execute(update(products).where(products.c.slug=='trail-pack').values(active=False))
        conn.execute(update(variants).where(variants.c.sku=='TOTE-NATURAL').values(active=False))
        conn.execute(update(categories).where(categories.c.slug=='camp').values(active=False))
    assert client.get('/api/products/trail-pack').status_code==404
    assert client.get('/api/products/market-tote').status_code==404
    assert client.get('/api/products?category=camp').json()['total']==0
    assert 'camp' not in {c['slug'] for c in client.get('/api/categories').json()}


def test_migration_seed_idempotence_and_database_constraints(catalogue):
    app,client,config,root=catalogue
    variants=app.state.metadata.tables['variants']
    with app.state.engine.begin() as conn:
        conn.execute(update(variants).where(variants.c.sku=='PACK-OLIVE-18').values(price_minor=239900,stock_quantity=0))
    for values in ({'price_minor':-1},{'stock_quantity':-1},{'currency':'USD'},{'sku':'BOTTLE-CLAY-750'}):
        with pytest.raises(IntegrityError),app.state.engine.begin() as conn:
            conn.execute(update(variants).where(variants.c.sku=='PACK-OLIVE-18').values(**values))
    restarted=create_app(config,'sqlite:///'+str(root/'catalogue.db'))
    with TestClient(restarted) as after:
        row=after.get('/api/products/trail-pack').json()['variants'][0]
        assert row['price_minor']==239900 and row['available'] is False
        assert after.get('/api/products').json()['total']==8


def test_generator_contract_and_seed_validation_are_explicit():
    spec=example_spec()
    generated=sources(prepare_spec(spec))
    assert 'CATALOGUE'==prepare_spec(spec).source_generation_strategy
    assert 'data-testid={ids.search}' in generated['frontend/src/App.tsx']
    assert json.loads(generated['frontend/src/ui-contract.json'])['ids']['search']=='catalogue-search'
    assert json.loads(generated['backend/migrations/0001.json'])['config']==spec.catalogue_contract.model_dump(mode='json')
    assert 'frontend/public/assets/pack-detail.svg' in generated
    for path,source in generated.items():
        if path.endswith('.py'):compile(source,path,'exec')
    invalid=spec.catalogue_contract.model_dump(mode='json')
    invalid['products'][0]['variants'][0]['price_minor']=True
    with pytest.raises(ValidationError):CatalogueContract.model_validate(invalid)
    invalid=spec.catalogue_contract.model_dump(mode='json')
    invalid['products'][0]['variants'][0]['sku']=invalid['products'][1]['variants'][0]['sku']
    with pytest.raises(ValidationError):CatalogueContract.model_validate(invalid)
    spec.requirements[0].description='Support checkout and payments'
    with pytest.raises(ValueError,match='exceeds'):prepare_spec(spec)
    assert CatalogueUIContract().selector('product','trail-pack')=='[data-testid="catalogue-product"][data-product-slug="trail-pack"]'
