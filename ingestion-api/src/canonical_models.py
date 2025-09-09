from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any


# Very basic schemas for demo purposes
class Party(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    address: str = ""


class ExtensionField(BaseModel):
    """A structured key-value pair for extensions."""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: Any


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: str
    description: str
    hs_code: str = Field("", description="Global 6-digit Harmonized System code")
    quantity: float
    unit_price: float
    currency: str
    origin_country: str = Field("", description="ISO 3166-1 alpha-2 code")
    extensions: List[ExtensionField] = Field(
        [], description="Field for national extensions like NICO"
    )


class CanonicalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str
    jurisdiction: str
    origin_country: str
    destination_country: str
    sender: Party
    recipient: Party
    items: List[Item]


class Tax(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    tax_type: str  # e.g., 'IGI', 'DTA', 'IVA'
    base_value: float
    rate: float
    amount: float


class Measure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    authority: str


class NeutralEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taxes: List[Tax]
    measures: List[Measure]
    evidence: List[Dict[str, Any]]
