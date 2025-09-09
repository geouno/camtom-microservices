import httpx


def calculate_ad_valorem(base_value: float, rate: float) -> float:
    """Calculates tax based on a percentage of the value."""
    return round(base_value * rate, 2)


def calculate_fixed_fee(amount: float) -> float:
    """Returns a fixed fee amount."""
    return round(amount, 2)


def calculate_per_unit(quantity: float, rate_per_unit: float) -> float:
    """Calculates tax based on quantity and a per-unit rate."""
    return round(quantity * rate_per_unit, 2)


def get_exchange_rate(base_currency: str, target_currency: str) -> float:
    """
    Fetches the latest exchange rate from the Frankfurter API.
    Returns 1.0 if the currencies are the same.
    """
    if base_currency.upper() == target_currency.upper():
        return 1.0

    try:
        url = f"https://api.frankfurter.dev/v1/latest?base={base_currency.upper()}&symbols={target_currency.upper()}"
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print("exchange rate data", data)
        rate = data["rates"][target_currency.upper()]
        return float(rate)
    except (httpx.RequestError, KeyError, TypeError) as e:
        raise ValueError(
            f"Could not fetch exchange rate for {base_currency}->{target_currency}: {e}"
        )
