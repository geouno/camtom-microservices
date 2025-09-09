from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from .local_packages.mx_a1_v0_1_0 import rules as mx_rules, output_adapter as mx_adapter

app = FastAPI(title="Evaluation Service")

# TODO: Import models below appropriately
class CanonicalDocumentModel(BaseModel):
    # A model for validation at this service boundary
    org_id: str
    jurisdiction: str
    items: list

class AdaptRequest(BaseModel):
    jurisdiction: str
    neutral_result: Dict[str, Any]
    canonical_doc: Dict[str, Any]


@app.post("/evaluate", summary="Evaluate a canonical document")
def evaluate_document(doc: CanonicalDocumentModel):
    if doc.jurisdiction.upper() == "MX":
        try:
            return mx_rules.evaluate(doc.model_dump())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MX evaluation failed: {e}")
    
    raise HTTPException(status_code=400, detail=f"Jurisdiction '{doc.jurisdiction}' not supported.")

@app.post("/adapt", summary="Adapt a neutral result to a country-specific format")
def adapt_result(req: AdaptRequest):
    if req.jurisdiction.upper() == "MX":
        try:
            return mx_adapter.adapt_to_pedimento_a1(req.neutral_result, req.canonical_doc)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MX adaptation failed: {e}")

    raise HTTPException(status_code=400, detail=f"Jurisdiction '{req.jurisdiction}' not supported for adaptation.")


@app.get("/health")
def health_check():
    return {"status": "ok"}
