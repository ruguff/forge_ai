"""Non-secret identity configuration for the reviewed account/admin module."""
from urllib.parse import urlsplit
from typing import Literal
from pydantic import Field,model_validator
from app.execution.spec.commerce_contract import StrictContract


class IdentityContract(StrictContract):
    version: Literal[1]=1
    public_origin: str=Field(default='https://store.example.invalid',max_length=200)
    allow_local_http: bool=False
    session_idle_seconds: int=Field(default=1800,ge=300,le=3600)
    session_absolute_seconds: int=Field(default=28800,ge=3600,le=86400)
    recovery_seconds: int=Field(default=900,ge=300,le=1800)

    @model_validator(mode='after')
    def origin_policy(self):
        url=urlsplit(self.public_origin)
        if url.username or url.password or url.path not in ('','/') or url.query or url.fragment or not url.hostname:
            raise ValueError('Use an exact origin without credentials, path, query or fragment')
        if url.scheme!='https' and not (self.allow_local_http and url.scheme=='http' and url.hostname in ('127.0.0.1','localhost','::1')):
            raise ValueError('HTTPS is required except explicitly enabled loopback development')
        if self.allow_local_http and url.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Local development mode is restricted to loopback origins')
        if self.session_idle_seconds>self.session_absolute_seconds:
            raise ValueError('Idle expiry cannot exceed absolute expiry')
        self.public_origin=self.public_origin.rstrip('/')
        return self
