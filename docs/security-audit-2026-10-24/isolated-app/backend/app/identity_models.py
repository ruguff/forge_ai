"""Reviewed identity and administrative input models; never accept client roles."""
import re
from pydantic import BaseModel,ConfigDict,Field,SecretStr,StrictInt,field_validator,model_validator
try:
    from .catalogue_models import CatalogueProduct,CatalogueCategory
except ModuleNotFoundError:
    from app.execution.spec.catalogue_contract import CatalogueProduct,CatalogueCategory


class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Credentials(Input):
    email: str=Field(min_length=3,max_length=254)
    password: SecretStr

    @field_validator('email')
    @classmethod
    def email_format(cls,value):
        value=value.strip().lower()
        if not re.fullmatch(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}',value):
            raise ValueError('Enter a valid email address')
        return value

    @field_validator('password')
    @classmethod
    def bounded_password(cls,value):
        if not 1<=len(value.get_secret_value())<=128:
            raise ValueError('Password length is invalid')
        return value


def strong_password(value):
    raw=value.get_secret_value()
    if not 15<=len(raw)<=128 or not raw.strip() or raw.lower() in ('passwordpassword','123456789012345','qwertyuiopasdfgh'):
        raise ValueError('Use a passphrase of 15–128 characters')
    return value


class Register(Credentials):
    name: str=Field(min_length=1,max_length=100)
    _strong=field_validator('password')(strong_password)

    @field_validator('name')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Name is required')
        return value.strip()


class Forgot(Input):
    email: str=Field(min_length=3,max_length=254)
    _email=field_validator('email')(Credentials.email_format.__func__)


class Reset(Input):
    token: str=Field(min_length=40,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    password: SecretStr
    _strong=field_validator('password')(strong_password)


class ChangePassword(Input):
    current_password: SecretStr
    password: SecretStr
    _bounded=field_validator('current_password')(Credentials.bounded_password.__func__)
    _strong=field_validator('password')(strong_password)


class Profile(Input):
    name: str=Field(min_length=1,max_length=100)
    _name=field_validator('name')(Register.nonblank.__func__)


class Address(Input):
    label: str=Field(min_length=1,max_length=50)
    full_name: str=Field(min_length=1,max_length=100)
    line1: str=Field(min_length=1,max_length=180)
    line2: str=Field(default='',max_length=180)
    city: str=Field(min_length=1,max_length=80)
    region: str=Field(min_length=1,max_length=80)
    postal_code: str=Field(min_length=1,max_length=20)
    country: str=Field(pattern=r'^[A-Z]{2}$')

    @field_validator('*')
    @classmethod
    def clean_text(cls,value,info):
        value=value.strip()
        if not value and info.field_name!='line2':raise ValueError('This address field is required')
        return value


class AdminProduct(CatalogueProduct):
    @model_validator(mode='after')
    def safe_content(self):
        text=[self.name,self.description,self.material]+[v.label for v in self.variants]+[i.alt for i in self.images]
        if any(not v.strip() for v in text):raise ValueError('Product text cannot be blank')
        if len({v.sku for v in self.variants})!=len(self.variants):raise ValueError('SKUs must be unique')
        return self


class ProductUpdate(Input):
    product: AdminProduct
    expected_version: StrictInt=Field(ge=1)


class StockUpdate(Input):
    quantity: StrictInt=Field(ge=0,le=1_000_000)
    expected_version: StrictInt=Field(ge=1)


class CategoryInput(CatalogueCategory):
    @field_validator('name')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Category name cannot be blank')
        return value.strip()
