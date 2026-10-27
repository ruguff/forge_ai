"""Explicit single-store rules. These are business configuration, not tax advice."""
from typing import Literal
from pydantic import Field,StrictInt
from app.execution.spec.commerce_contract import StrictContract
class OrderContract(StrictContract):
    version:Literal[1]=1
    tax_basis_points:StrictInt=Field(ge=0,le=10000)
    shipping_minor:StrictInt=Field(ge=0,le=1000000)
    discount_basis_points:StrictInt=Field(ge=0,le=10000)
    reservation_seconds:StrictInt=Field(default=900,ge=60,le=3600)
    policy_label:str=Field(min_length=1,max_length=160)
