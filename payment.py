from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Custom exception for payment errors."""
    pass


def calculate_total(
    price: float,
    quantity: int,
    discount: float = 0.0
) -> float:
    """
    Calculate total price with optional discount.

    Args:
        price:    Unit price (must be non-negative).
        quantity: Number of units (must be positive).
        discount: Fractional discount in [0, 1] (default 0.0).

    Returns:
        Total price after discount.

    Raises:
        ValueError: If any argument is out of range or wrong type.
    """
    # --- type validation ---
    if not isinstance(price, (int, float)):
        raise ValueError("Price must be a number")
    if not isinstance(quantity, int):
        raise ValueError("Quantity must be an integer")
    if not isinstance(discount, (int, float)):
        raise ValueError("Discount must be a number")

    # --- range validation ---
    if price < 0:
        raise ValueError("Price cannot be negative")
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if not 0 <= discount <= 1:
        raise ValueError("Discount must be between 0 and 1")

    subtotal = price * quantity
    return subtotal * (1 - discount)


def process_payment(
    amount: float,
    currency: str = "USD",
    max_amount: float = 1_000_000.0
) -> dict:
    """
    Process a payment safely.

    Args:
        amount:     Payment amount (must be positive and within max_amount).
        currency:   ISO-4217 currency code, e.g. "USD" (must be 3 characters).
        max_amount: Upper sanity limit for the amount (default 1,000,000).

    Returns:
        A dict with keys: status, amount, currency.

    Raises:
        PaymentError: If amount or currency is invalid.
    """
    if not isinstance(amount, (int, float)):
        raise PaymentError("Payment amount must be a number")
    if amount <= 0:
        raise PaymentError("Payment amount must be positive")
    if amount > max_amount:
        raise PaymentError(f"Amount exceeds maximum allowed limit of {max_amount}")

    if not currency or not isinstance(currency, str) or len(currency) != 3:
        raise PaymentError("Invalid currency code — must be a 3-letter ISO code")

    currency = currency.upper()
    logger.info(f"Processing payment of {amount} {currency}")

    return {
        "status":   "success",
        "amount":   amount,
        "currency": currency,
    }


def get_payment_history(user: Optional[dict]) -> list:
    """
    Safely retrieve payment history for a user.

    Args:
        user: A user dict that may contain a "payment_history" key,
              or None.

    Returns:
        A list of valid payment dicts; empty list if user is None
        or has no history.
    """
    if not user:
        return []

    history = user.get("payment_history", [])

    # Filter out None entries AND non-dict entries for extra safety
    return [p for p in history if isinstance(p, dict)]


def apply_discount(
    price: float,
    discount_code: str,
    valid_codes: dict
) -> float:
    """
    Apply a discount code to a price safely.

    Args:
        price:         Original price (must be non-negative).
        discount_code: Code string to look up.
        valid_codes:   Mapping of code -> fractional discount in [0, 1].

    Returns:
        Discounted price, or the original price if the code is
        missing / invalid.

    Raises:
        ValueError: If price is negative.
    """
    if not isinstance(price, (int, float)):
        raise ValueError("Price must be a number")
    if price < 0:
        raise ValueError("Price cannot be negative")

    if not discount_code or not valid_codes:
        return price

    discount = valid_codes.get(discount_code, 0.0)

    # Guard against bad data in valid_codes
    if not isinstance(discount, (int, float)) or not 0 <= discount <= 1:
        logger.warning(
            f"Discount code '{discount_code}' has invalid discount value "
            f"'{discount}'. Returning original price."
        )
        return price

    return price * (1 - discount)