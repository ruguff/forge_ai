"""Bounded, credential-free configuration for the reviewed read-only catalogue."""
from typing import Literal
from pydantic import Field, StrictInt, field_validator, model_validator
from pydantic import BaseModel, ConfigDict
class StrictContract(BaseModel):
    model_config=ConfigDict(extra='forbid')

Slug = str
Asset = Literal['pack', 'pack-detail', 'bottle', 'lamp', 'stool', 'tote', 'blanket']


class CatalogueCategory(StrictContract):
    slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', max_length=60)
    name: str = Field(min_length=1, max_length=80)
    active: bool = True


class CatalogueVariant(StrictContract):
    sku: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
    label: str = Field(min_length=1, max_length=80)
    options: dict[str, str] = Field(default_factory=dict, max_length=5)
    price_minor: StrictInt = Field(ge=0, le=2_000_000_000)
    stock_quantity: StrictInt = Field(ge=0, le=1_000_000)
    active: bool = True

    @field_validator('options')
    @classmethod
    def bounded_options(cls, value):
        if any(not k.strip() or not v.strip() or len(k) > 40 or len(v) > 60 for k,v in value.items()):
            raise ValueError('Options must have short, nonblank labels and values')
        return value


class CatalogueImage(StrictContract):
    asset: Asset
    alt: str = Field(min_length=1, max_length=180)


class CatalogueProduct(StrictContract):
    slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', max_length=80)
    category_slug: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=3000)
    material: str = Field(min_length=1, max_length=160)
    active: bool = True
    variants: list[CatalogueVariant] = Field(min_length=1, max_length=24)
    images: list[CatalogueImage] = Field(min_length=1, max_length=8)


class CatalogueContract(StrictContract):
    version: Literal[1] = 1
    store_name: str = Field(min_length=1, max_length=60)
    tagline: str = Field(default='Considered essentials. Everyday adventures.', min_length=1, max_length=100)
    currency: Literal['INR', 'USD', 'EUR', 'GBP'] = 'INR'
    theme: Literal['sand-olive'] = 'sand-olive'
    categories: list[CatalogueCategory] = Field(min_length=1, max_length=12)
    products: list[CatalogueProduct] = Field(min_length=1, max_length=120)

    @model_validator(mode='after')
    def references_and_unique_keys(self):
        categories = [c.slug for c in self.categories]
        slugs = [p.slug for p in self.products]
        skus = [v.sku for p in self.products for v in p.variants]
        if len(set(categories)) != len(categories) or len(set(slugs)) != len(slugs) or len(set(skus)) != len(skus):
            raise ValueError('Category slugs, product slugs and SKUs must be unique')
        if any(p.category_slug not in categories for p in self.products):
            raise ValueError('Every product must reference a declared category')
        for value in [self.store_name,self.tagline] + [c.name for c in self.categories] + [s for p in self.products for s in (p.name,p.description,p.material)] + [v.label for p in self.products for v in p.variants] + [i.alt for p in self.products for i in p.images]:
            if not value.strip():
                raise ValueError('Catalogue text cannot be blank')
        return self
