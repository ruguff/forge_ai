"""Typed commerce contracts. Unsupported execution must remain blocked."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

class StrictContract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Relationship(StrictContract):
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    on_delete: Literal['RESTRICT', 'CASCADE', 'SET NULL'] = 'RESTRICT'


class RelationalContract(StrictContract):
    """Initial migration and related CRUD only; not commerce business logic."""
    version: Literal[1] = 1
    relationships: list[Relationship] = Field(default_factory=list)
    migration_revision: Literal['0001'] = '0001'


class Migration(StrictContract):
    revision: str = Field(pattern=r'^[a-zA-Z0-9_]+$')
    parent: str | None = None
    description: str
    # Reviewed compiler emits SQL; model supplies no executable SQL.


class Permission(StrictContract):
    operation_id: str
    roles: list[Literal['anonymous', 'customer', 'admin']]
    ownership_field: str | None = None


class StateTransition(StrictContract):
    aggregate: Literal['order', 'payment', 'refund', 'reservation']
    from_state: str
    to_state: str
    operation: str
    roles: list[Literal['customer', 'admin', 'payment_provider', 'system']]


class BusinessRule(StrictContract):
    rule_id: str
    module: Literal['pricing', 'inventory', 'checkout', 'orders', 'payments', 'refunds']
    requirement_ids: list[str] = Field(min_length=1)
    description: str


class PaymentIntegration(StrictContract):
    provider: Literal['offline_simulator', 'razorpay_test'] = 'offline_simulator'
    live_enabled: Literal[False] = False
    currency: str = Field(default='INR', pattern=r'^[A-Z]{3}$')
    credential_env_names: list[str] = Field(default_factory=list)


class CommerceContract(StrictContract):
    version: Literal[1] = 1
    store_mode: Literal['single_store'] = 'single_store'
    database: Literal['postgresql'] = 'postgresql'
    relationships: list[Relationship] = Field(default_factory=list)
    migrations: list[Migration] = Field(default_factory=list)
    permissions: list[Permission] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)
    state_transitions: list[StateTransition] = Field(default_factory=list)
    payment: PaymentIntegration = Field(default_factory=PaymentIntegration)
    tax_configuration: dict = Field(default_factory=dict)
    shipping_configuration: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def migration_chain(self):
        seen = set()
        previous = None
        for migration in self.migrations:
            if migration.revision in seen or migration.parent != previous:
                raise ValueError('Migrations must form a unique ordered linear chain')
            seen.add(migration.revision)
            previous = migration.revision
        return self
