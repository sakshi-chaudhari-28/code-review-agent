from typing import Optional
import logging

logger = logging.getLogger(__name__)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string."""
    if not isinstance(amount, (int, float)):
        raise ValueError("Amount must be a number")
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return f"{currency} {amount:.2f}"


def is_valid_currency(currency: str) -> bool:
    """Check if currency code is valid ISO-4217."""
    if not currency or not isinstance(currency, str):
        return False
    valid = {"USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD"}
    return currency.upper() in valid


def calculate_tax(amount: float, tax_rate: float) -> float:
    """Calculate tax amount safely."""
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    if not 0 <= tax_rate <= 1:
        raise ValueError("Tax rate must be between 0 and 1")
    return round(amount * tax_rate, 2)


def split_bill(total: float, people: int) -> float:
    """Split bill equally among people."""
    if total < 0:
        raise ValueError("Total cannot be negative")
    if people <= 0:
        raise ValueError("Number of people must be positive")
    return round(total / people, 2)