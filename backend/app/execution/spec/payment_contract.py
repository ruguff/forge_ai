"""Explicit offline simulation only. Provider credentials are never accepted here."""
from typing import Literal
from app.execution.spec.commerce_contract import StrictContract


class PaymentSimulationContract(StrictContract):
    version: Literal[1] = 1
    mode: Literal['offline_simulator'] = 'offline_simulator'
    refunds: Literal['admin_full_only'] = 'admin_full_only'
