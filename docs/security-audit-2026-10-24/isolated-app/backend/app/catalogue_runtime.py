"""Reviewed public catalogue. Mutations, identity and checkout are separate phases."""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import (MetaData, Table, Column, Integer, Text, Boolean, JSON, ForeignKey,
                        CheckConstraint, UniqueConstraint, create_engine, event, select, func, case, and_, or_)
try:
    from .relational_runtime import migrate
except ImportError:
    from app.execution.agent.relational_runtime import migrate


def metadata_for(currency):
    metadata = MetaData()
    Table('categories',metadata,
        Column('id',Integer,primary_key=True),Column('slug',Text,nullable=False,unique=True),
        Column('name',Text,nullable=False),Column('active',Boolean,nullable=False))
    Table('products',metadata,
        Column('id',Integer,primary_key=True),Column('slug',Text,nullable=False,unique=True),
        Column('category_id',Integer,ForeignKey('categories.id',ondelete='RESTRICT'),nullable=False,index=True),
        Column('name',Text,nullable=False),Column('description',Text,nullable=False),
        Column('material',Text,nullable=False),Column('active',Boolean,nullable=False))
    Table('variants',metadata,
        Column('id',Integer,primary_key=True),Column('product_id',Integer,ForeignKey('products.id',ondelete='CASCADE'),nullable=False,index=True),
        Column('sku',Text,nullable=False,unique=True),Column('label',Text,nullable=False),Column('options',JSON,nullable=False),
        Column('price_minor',Integer,nullable=False),Column('currency',Text,nullable=False),
        Column('stock_quantity',Integer,nullable=False),Column('active',Boolean,nullable=False),
        CheckConstraint('price_minor >= 0 AND price_minor <= 2000000000',name='valid_price_minor'),
        CheckConstraint('stock_quantity >= 0 AND stock_quantity <= 1000000',name='valid_stock_quantity'),
        CheckConstraint("currency = '"+currency+"'",name='store_currency'))
    Table('product_images',metadata,
        Column('id',Integer,primary_key=True),Column('product_id',Integer,ForeignKey('products.id',ondelete='CASCADE'),nullable=False,index=True),
        Column('asset',Text,nullable=False),Column('alt',Text,nullable=False),Column('position',Integer,nullable=False),
        UniqueConstraint('product_id','position',name='image_order'),CheckConstraint('position >= 0',name='nonnegative_image_order'),
        CheckConstraint("asset IN ('pack','pack-detail','bottle','lamp','stool','tote','blanket')",name='reviewed_local_image'))
    # A separate seed marker makes repeated startups preserve catalogue edits.
    Table('catalogue_seed',metadata,Column('id',Integer,primary_key=True))
    return metadata


def seed_database(engine,metadata,config):
    cats,products,variants,images,marker = (metadata.tables[t] for t in ('categories','products','variants','product_images','catalogue_seed'))
    with engine.begin() as conn:
        if engine.dialect.name == 'postgresql':
            from sqlalchemy import text
            conn.execute(text('SELECT pg_advisory_xact_lock(681072015)'))
        if conn.execute(select(marker.c.id)).first():
            return
        if conn.execute(select(products.c.id)).first() or conn.execute(select(cats.c.id)).first():
            raise RuntimeError('Refusing to seed unmarked existing catalogue data')
        category_ids = {}
        for category in config['categories']:
            category_ids[category['slug']] = conn.execute(cats.insert().values(**category)).inserted_primary_key[0]
        for product in config['products']:
            values = {k:product[k] for k in ('slug','name','description','material','active')}
            values['category_id'] = category_ids[product['category_slug']]
            pid = conn.execute(products.insert().values(**values)).inserted_primary_key[0]
            for variant in product['variants']:
                conn.execute(variants.insert().values(product_id=pid,currency=config['currency'],**variant))
            for position,image in enumerate(product['images']):
                conn.execute(images.insert().values(product_id=pid,position=position,**image))
        conn.execute(marker.insert().values(id=1))


def create_app(config_path=None,database_url=None,migration_followups=None):
    path = Path(config_path or Path(__file__).with_name('catalogue.json'))
    config = json.loads(path.read_text(encoding='utf-8'))
    # Config was validated by the compiler; enforce the currency allowlist again
    # before using it in the fixed CHECK expression.
    if config.get('currency') not in ('INR','USD','EUR','GBP'):
        raise RuntimeError('Unsupported catalogue currency')
    manifest = path.parent.parent/'migrations/0001.json'
    schema = {'module':'catalogue-v1','database':'postgresql','config':config}
    if config_path is None and json.loads(manifest.read_text(encoding='utf-8')) != schema:
        raise RuntimeError('Catalogue migration manifest mismatch')
    url = database_url or os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL must reference the configured PostgreSQL database')
    # Explicit SQLite URLs are accepted only by the reviewed-module unit tests.
    if config_path is None and not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Generated catalogue requires PostgreSQL; no provider substitution')
    engine = create_engine(url,connect_args={'check_same_thread':False} if url.startswith('sqlite') else {},pool_pre_ping=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine,'connect')
        def enable_foreign_keys(connection,_):
            connection.execute('PRAGMA foreign_keys=ON')
    metadata = metadata_for(config['currency'])
    @asynccontextmanager
    async def lifespan(app):
        migrate(engine,schema,metadata,followups=migration_followups)
        seed_database(engine,metadata,config)
        yield
        engine.dispose()
    app = FastAPI(title=config['store_name']+' catalogue',lifespan=lifespan)
    app.state.engine, app.state.metadata = engine,metadata
    p,c,v,img = (metadata.tables[t] for t in ('products','categories','variants','product_images'))

    def image_response(row):
        return {'url':'/assets/'+row['asset']+'.svg','alt':row['alt']}

    def image_map(conn,ids):
        grouped = {pid:[] for pid in ids}
        if ids:
            for row in conn.execute(select(img).where(img.c.product_id.in_(ids)).order_by(img.c.position,img.c.id)).mappings():
                grouped[row['product_id']].append(image_response(row))
        return grouped

    @app.get('/api/store')
    def store():
        return {'name':config['store_name'],'tagline':config['tagline'],'currency':config['currency'],
                'capabilities':{'catalogue':True,'accounts':bool(getattr(app.state,'identity_enabled',False)),'checkout':bool(getattr(app.state,'order_enabled',False)),'payments':False}}

    @app.get('/api/categories')
    def categories():
        with engine.connect() as conn:
            available = select(v.c.product_id).where(v.c.active.is_(True)).distinct().subquery()
            counts = select(p.c.category_id,func.count().label('count')).join(available,available.c.product_id==p.c.id).where(p.c.active.is_(True)).group_by(p.c.category_id).subquery()
            rows = conn.execute(select(c.c.slug,c.c.name,func.coalesce(counts.c.count,0).label('count')).outerjoin(counts,counts.c.category_id==c.c.id).where(c.c.active.is_(True)).order_by(c.c.id)).mappings()
            return [dict(row) for row in rows]

    @app.get('/api/products')
    def products(q: str = Query('',max_length=100),category: str | None = Query(None,max_length=60),
                 min_price: int | None = Query(None,ge=0,le=2_000_000_000),max_price: int | None = Query(None,ge=0,le=2_000_000_000),
                 in_stock: bool = False,sort: Literal['featured','price-asc','price-desc','name'] = 'featured',
                 page: int = Query(1,ge=1,le=10000),limit: int = Query(12,ge=1,le=48)):
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(422,'Minimum price must not exceed maximum price')
        variant_filters = [v.c.active.is_(True)]
        if min_price is not None: variant_filters.append(v.c.price_minor >= min_price)
        if max_price is not None: variant_filters.append(v.c.price_minor <= max_price)
        if in_stock: variant_filters.append(v.c.stock_quantity > 0)
        offers = select(v.c.product_id,func.min(v.c.price_minor).label('price_minor'),func.max(v.c.price_minor).label('max_price_minor'),
            func.max(case((v.c.stock_quantity > 0,1),else_=0)).label('available')).where(*variant_filters).group_by(v.c.product_id).subquery()
        query = select(p.c.id,p.c.slug,p.c.name,p.c.material,c.c.name.label('category'),c.c.slug.label('category_slug'),
            offers.c.price_minor,offers.c.max_price_minor,offers.c.available).join(c,c.c.id==p.c.category_id).join(offers,offers.c.product_id==p.c.id).where(p.c.active.is_(True),c.c.active.is_(True))
        term = q.strip()
        if term:
            escaped = term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            pattern = '%'+escaped+'%'
            matching_skus = select(v.c.product_id).where(v.c.active.is_(True),v.c.sku.ilike(pattern,escape='\\'))
            query = query.where(or_(p.c.name.ilike(pattern,escape='\\'),p.c.description.ilike(pattern,escape='\\'),p.c.id.in_(matching_skus)))
        if category: query = query.where(c.c.slug == category)
        ordering = {'featured':p.c.id,'name':p.c.name,'price-asc':offers.c.price_minor,'price-desc':offers.c.price_minor.desc()}[sort]
        with engine.connect() as conn:
            total = conn.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            rows = conn.execute(query.order_by(ordering,p.c.id).offset((page-1)*limit).limit(limit)).mappings().all()
            images = image_map(conn,[row['id'] for row in rows])
            items = [{**dict(row),'available':bool(row['available']),'currency':config['currency'],'images':images[row['id']]} for row in rows]
            return {'items':items,'total':total,'page':page,'limit':limit}

    @app.get('/api/products/{slug}')
    def product_detail(slug: str):
        with engine.connect() as conn:
            row = conn.execute(select(p,c.c.name.label('category'),c.c.slug.label('category_slug')).join(c,c.c.id==p.c.category_id).where(p.c.slug==slug,p.c.active.is_(True),c.c.active.is_(True))).mappings().first()
            if row is None: raise HTTPException(404,'Product not found')
            variants = conn.execute(select(v).where(v.c.product_id==row['id'],v.c.active.is_(True)).order_by(v.c.id)).mappings().all()
            if not variants: raise HTTPException(404,'Product not found')
            return {**dict(row),'images':image_map(conn,[row['id']])[row['id']],
                'variants':[{k:variant[k] for k in ('id','sku','label','options','price_minor','currency')} |
                            {'available':variant['stock_quantity']>0} for variant in variants]}
    return app
