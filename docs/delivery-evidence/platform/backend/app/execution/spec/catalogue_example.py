"""Small reproducible seed catalogue for generation and independent acceptance."""
from app.execution.spec.build_spec_models import BuildSpec, TechStackSelection, APIEndpointDef, BuildRequirementItem
from app.execution.spec.catalogue_contract import CatalogueContract
from app.execution.agent.catalogue import ROUTES


def example_spec():
    products = [
        dict(slug='trail-pack',category_slug='carry',name='The trail pack',material='Waxed canvas · 18 L',
             description='A compact canvas pack with a roomy front pocket and adjustable straps. An illustrated sample product for everyday carrying.',
             images=[{'asset':'pack','alt':'Olive canvas backpack illustration'},{'asset':'pack-detail','alt':'Close-up illustration of the backpack pocket and straps'}],
             variants=[dict(sku='PACK-OLIVE-18',label='Olive · 18 L',options={'Colour':'Olive','Capacity':'18 L'},price_minor=249900,stock_quantity=12),
                       dict(sku='PACK-SAND-18',label='Sand · 18 L',options={'Colour':'Sand','Capacity':'18 L'},price_minor=259900,stock_quantity=0)]),
        dict(slug='everyday-bottle',category_slug='drinkware',name='The everyday bottle',material='Stainless steel · 750 ml',
             description='A simple reusable bottle with a carry loop and a powder-coated finish. An illustrated sample for everyday outings.',
             images=[{'asset':'bottle','alt':'Terracotta reusable bottle illustration'}],
             variants=[dict(sku='BOTTLE-CLAY-750',label='Clay · 750 ml',options={'Colour':'Clay','Capacity':'750 ml'},price_minor=129900,stock_quantity=20)]),
        dict(slug='weekend-lantern',category_slug='camp',name='The weekend lantern',material='Metal frame · Warm light',
             description='A portable lantern with a carrying handle and a warm diffused glow. An illustrated example for a slower evening outdoors.',
             images=[{'asset':'lamp','alt':'Olive framed lantern with warm light illustration'}],
             variants=[dict(sku='LANTERN-OLIVE',label='Olive',options={'Colour':'Olive'},price_minor=189900,stock_quantity=0)]),
        dict(slug='folding-stool',category_slug='camp',name='The folding stool',material='Canvas seat · Timber frame',
             description='A compact folding seat with a canvas sling and crossed timber legs. An illustrated sample for taking a break.',
             images=[{'asset':'stool','alt':'Canvas folding stool on a timber frame illustration'}],
             variants=[dict(sku='STOOL-FERN',label='Fern',options={'Colour':'Fern'},price_minor=219900,stock_quantity=8)]),
        dict(slug='market-tote',category_slug='carry',name='The market tote',material='Cotton canvas · Natural',
             description='An open-top canvas tote with long handles and space for everyday essentials. An illustrated sample of a practical carry bag.',
             images=[{'asset':'tote','alt':'Natural canvas tote bag illustration'}],
             variants=[dict(sku='TOTE-NATURAL',label='Natural',options={'Colour':'Natural'},price_minor=89900,stock_quantity=30)]),
        dict(slug='woven-throw',category_slug='home',name='The woven throw',material='Woven blend · 130 × 170 cm',
             description='A striped throw with fringed edges for a quiet corner at home. An illustrated sample with warm earthy colours.',
             images=[{'asset':'blanket','alt':'Terracotta striped throw with fringed edges illustration'}],
             variants=[dict(sku='THROW-TERRA',label='Terra',options={'Colour':'Terra'},price_minor=279900,stock_quantity=6)]),
        dict(slug='daily-pack',category_slug='carry',name='The daily pack',material='Canvas · 12 L',
             description='A smaller canvas pack for light journeys. Illustrated example from the carry collection.',
             images=[{'asset':'pack','alt':'Compact olive backpack illustration'}],
             variants=[dict(sku='PACK-DAILY-12',label='Olive · 12 L',options={'Capacity':'12 L'},price_minor=199900,stock_quantity=7)]),
        dict(slug='small-bottle',category_slug='drinkware',name='The small bottle',material='Stainless steel · 500 ml',
             description='A smaller reusable bottle for carrying light. Illustrated example from the drinkware collection.',
             images=[{'asset':'bottle','alt':'Small terracotta reusable bottle illustration'}],
             variants=[dict(sku='BOTTLE-CLAY-500',label='Clay · 500 ml',options={'Capacity':'500 ml'},price_minor=109900,stock_quantity=10)]),
    ]
    contract = CatalogueContract(store_name='fieldwork',tagline='A thoughtful collection of useful things, for the everyday and the outside.',currency='INR',
        categories=[{'slug':'carry','name':'Carry'},{'slug':'drinkware','name':'Drinkware'},{'slug':'camp','name':'Camp'},{'slug':'home','name':'Home'}],products=products)
    requirements = [BuildRequirementItem(id='CAT-001',title='Public product catalogue',
        description='Browse product details, categories, variants, SKU availability and images; search, filter and paginate catalogue results.',source='USER')]
    return BuildSpec(project_id='PROJ-CATALOGUE-DEMO',project_name='Fieldwork catalogue',generation_mode='MODEL',source_generation_strategy='CATALOGUE',
        catalogue_contract=contract,tech_stack=TechStackSelection(primary_database='PostgreSQL',auth_provider='None',frontend_styling='CSS'),
        requirements=requirements,api_endpoints=[APIEndpointDef(endpoint_id='CATALOGUE-'+str(i),method='GET',path=path,description=description,auth_required=False,traceable_requirements=['CAT-001']) for i,(path,description) in enumerate(ROUTES)])
