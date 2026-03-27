"""
Application-wide constants.
Centralises all magic numbers and strings to avoid scattered literals.
"""

# Pagination
DEFAULT_PAGE_SIZE: int = 10

# Payment
ACCEPTED_CRYPTO_ASSETS: str = "TON,USDT,BTC,ETH"
INVOICE_COOLDOWN_SECONDS: float = 30.0
PAYMENT_STATUS_PENDING: str = "pending"
PAYMENT_STATUS_SUCCEEDED: str = "succeeded"
PAYMENT_STATUS_FAILED: str = "failed"

# Cart
CART_MAX_ITEMS: int = 10

# Broadcast
BROADCAST_BATCH_SIZE: int = 30
BROADCAST_BATCH_DELAY: float = 1.0
BROADCAST_PROGRESS_THROTTLE: float = 2.0
