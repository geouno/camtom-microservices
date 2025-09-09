import json
from pathlib import Path
from typing import Dict, Any
from ...global_core import primitives

# Load table data
PACKAGE_DIR = Path(__file__).parent
with open(PACKAGE_DIR / "tables.json") as f:
    tables = json.load(f)


def evaluate(canonical_doc: Dict[str, Any]) -> Dict[str, Any]:
    all_taxes = []
    all_measures = []
    all_evidence = []
    total_customs_value = 0.0
    total_igi_amount = 0.0

    if not canonical_doc.get("items"):
        return {"taxes": [], "measures": [], "evidence": []}

    # Exchange Rate Logic
    # Assume the currency of the first item applies to the entire document for MVP.
    first_item_currency = canonical_doc["items"][0].get("currency", "MXN")
    TARGET_CURRENCY = "MXN"
    exchange_rate = primitives.get_exchange_rate(first_item_currency, TARGET_CURRENCY)
    all_evidence.append({
        "rule": "exchange_rate.lookup",
        "inputs": {"base_currency": first_item_currency},
        "outputs": {"exchange_rate": exchange_rate},
    })

    # 1. Per-Item Calculations (IGI and NOMs)
    # Iterate through each item to calculate its specific duties and regulations.
    for item in canonical_doc["items"]:
        item_line_id = item.get("line_id", "N/A")
        item_value = item.get("quantity", 0) * item.get("unit_price", 0)
        item_customs_value = round(item_value * exchange_rate, 2)
        total_customs_value += item_customs_value

        # Make sure extensions are a dict
        item_extensions = {ext.get("key"): ext.get("value") for ext in item.get("extensions", [])}
        item_nico = item_extensions.get("MX_NICO", "")
        item_hs_code = item.get("hs_code", "")

        # IGI Lookup for the current item
        igi_rate = 0.0
        for tariff in tables.get("igi_tariffs", []):
            if tariff.get("hs_code") == item_hs_code and tariff.get("nico") == item_nico:
                igi_rate = tariff.get("rate", 0.0)
                break

        igi_amount = primitives.calculate_ad_valorem(item_customs_value, igi_rate)
        if igi_amount > 0:
            total_igi_amount += igi_amount
            all_taxes.append({
                "name": f"IGI (Item {item_line_id})",
                "tax_type": "Import Duty",
                "base_value": item_customs_value,
                "rate": igi_rate,
                "amount": igi_amount,
            })
            all_evidence.append({
                "rule": "igi.lookup",
                "inputs": {"line_id": item_line_id, "hs": item_hs_code, "nico": item_nico},
                "outputs": {"amount": igi_amount},
            })

        # NOMs Lookup for the current item
        for nom in tables.get("noms", []):
            if nom.get("hs_code") == item_hs_code and nom.get("nico") == item_nico:
                all_measures.append({
                    "name": nom.get("measure_name"),
                    "description": nom.get("description"),
                    "authority": nom.get("authority"),
                })
                all_evidence.append({
                    "rule": "nom.lookup",
                    "inputs": {"line_id": item_line_id, "hs": item_hs_code},
                    "outputs": {"measure": nom.get("measure_name")},
                })

    # 2. Shipment-Level Calculations (DTA and IVA)
    # These are calculated on the aggregated totals of all items.

    # DTA (Derecho de Trámite Aduanero)
    dta_rule = tables.get("dta", {})
    dta_rate = dta_rule.get("rate", 0.0)
    dta_amount = primitives.calculate_ad_valorem(total_customs_value, dta_rate)
    if dta_amount > 0:
        all_taxes.append({
            "name": "DTA",
            "tax_type": "Customs Fee",
            "base_value": total_customs_value,
            "rate": dta_rate,
            "amount": dta_amount,
        })
        all_evidence.append({
            "rule": "dta.apply_standard_rate",
            "inputs": {"total_customs_value": total_customs_value},
            "outputs": {"amount": dta_amount},
        })

    # IVA (Impuesto al Valor Agregado)
    iva_base = total_customs_value + total_igi_amount + dta_amount
    iva_rule = tables.get("iva", {})
    iva_rate = iva_rule.get("standard_rate", 0.0)
    iva_amount = primitives.calculate_ad_valorem(iva_base, iva_rate)
    if iva_amount > 0:
        all_taxes.append({
            "name": "IVA",
            "tax_type": "VAT",
            "base_value": round(iva_base, 2),
            "rate": iva_rate,
            "amount": iva_amount,
        })
        all_evidence.append({
            "rule": "iva.on_base_plus_duties",
            "inputs": {"base": round(iva_base, 2)},
            "outputs": {"amount": iva_amount},
        })

    return {"taxes": all_taxes, "measures": all_measures, "evidence": all_evidence}
