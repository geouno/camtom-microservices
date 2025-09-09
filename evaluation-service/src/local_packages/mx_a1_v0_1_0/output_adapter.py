from typing import Dict, Any


def adapt_to_pedimento_a1(
    neutral_result: Dict[str, Any], canonical_doc: Dict[str, Any]
) -> Dict[str, Any]:
    # Simplified Pedimento A1 output for demo purposes
    item = canonical_doc["items"][0]

    contributions = {tax["name"]: tax["amount"] for tax in neutral_result["taxes"]}

    # Make sure extensions are a dict
    item_extensions = {ext["key"]: ext["value"] for ext in item.get("extensions", [])}
    item_nico = item_extensions.get("MX_NICO", "00")

    lookup = next(
        (
            x
            for x in neutral_result["evidence"]
            if x.get("rule") == "exchange_rate.lookup"
        ),
        None,
    )
    exchange_rate = 1.0 if lookup is None else lookup["outputs"]["exchange_rate"]

    return {
        "header": {
            "pedimento_type": "A1",
            "jurisdiction": "MX",
            "importer_rfc": "ABC123456789",  # Placeholder
            "customs_agent_patente": "3000",  # Placeholder
        },
        "line_items": [
            {
                "line_id": item["line_id"],
                "fraccion_arancelaria": f"{item['hs_code']}.{item_nico}",
                "description": item["description"],
                "customs_value_mxn": item["quantity"]
                * item["unit_price"]  # Assume MXN for demo
                * exchange_rate,
                "contributions": {
                    "IGI": contributions.get("IGI", 0),
                    "DTA": contributions.get("DTA", 0),
                    "IVA": contributions.get("IVA", 0),
                },
                "non_tariff_regulations": [
                    {"code": measure["name"]} for measure in neutral_result["measures"]
                ],
            }
        ],
        "totals": {
            "total_igi": contributions.get("IGI", 0),
            "total_dta": contributions.get("DTA", 0),
            "total_iva": contributions.get("IVA", 0),
            "total_paid": sum(contributions.values()),
        },
    }
