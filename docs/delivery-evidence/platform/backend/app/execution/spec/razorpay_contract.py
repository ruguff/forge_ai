"""Non-secret test integration configuration. Live mode is not supported."""
from typing import Literal
from app.execution.spec.commerce_contract import StrictContract


class RazorpayTestContract(StrictContract):
    version: Literal[1] = 1
    mode: Literal['razorpay_test'] = 'razorpay_test'
    currency: Literal['INR'] = 'INR'
    refunds: Literal['admin_full_only'] = 'admin_full_only'
