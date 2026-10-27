"""Shared public selectors; acceptance data never defines generated controls."""
from pydantic import BaseModel
from typing import Literal


class CatalogueUIContract(BaseModel):
    version: Literal[1] = 1

    def selector(self, control: str, slug: str | None = None):
        if control not in CONTROLS:
            raise ValueError('Unknown catalogue control')
        selector = '[data-testid="catalogue-'+control+'"]'
        if slug is not None:
            import re
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):
                raise ValueError('Invalid product slug')
            selector += '[data-product-slug="'+slug+'"]'
        return selector


CONTROLS = ('search','category','sort','min-price','max-price','stock','apply','clear',
            'results','product','loading','error','retry','empty','next','previous',
            'detail','variant','sku','price','availability','gallery','back')


def ui_manifest():
    return {'version':1,'ids':{control:'catalogue-'+control for control in CONTROLS}}
