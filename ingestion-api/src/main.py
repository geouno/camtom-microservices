import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import httpx
from .canonical_models import CanonicalDocument, NeutralEvaluationResult
from .genai_parser import parse_image_to_canonical

app = FastAPI(title="Ingestion API")
EVALUATION_SERVICE_URL = os.environ.get("EVALUATION_SERVICE_URL")


@app.post("/documents/process", summary="Upload, Parse, Evaluate, and Adapt a Document")
async def process_document(
    file: UploadFile = File(...),
    jurisdiction: str = Form(...),
    org_id: str = Form(...),
):
    filename = getattr(file, "filename", None)
    if not filename or not isinstance(filename, str):
        raise HTTPException(status_code=400, detail="No file uploaded.")
    if not filename.lower().endswith(".jpg") and not filename.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="Only JPG/PNG files are supported.")
    if not EVALUATION_SERVICE_URL:
        raise HTTPException(
            status_code=500, detail="EVALUATION_SERVICE_URL not configured."
        )

    try:
        pdf_bytes = await file.read()
        # Layer 1: Ingestion & Parsing
        canonical_doc: CanonicalDocument = parse_image_to_canonical(
            pdf_bytes, org_id, jurisdiction
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Layer 5: Rule Evaluation
            eval_response = await client.post(
                f"{EVALUATION_SERVICE_URL}/evaluate", json=canonical_doc.model_dump()
            )
            eval_response.raise_for_status()
            evaluation_result = eval_response.json()
            neutral_result = NeutralEvaluationResult(**evaluation_result)

            # Layer 6: Output Adaptation
            adapt_payload = {
                "jurisdiction": jurisdiction,
                "neutral_result": neutral_result.model_dump(),
                "canonical_doc": canonical_doc.model_dump(),
            }
            adapt_response = await client.post(
                f"{EVALUATION_SERVICE_URL}/adapt", json=adapt_payload
            )
            adapt_response.raise_for_status()
            final_declaration = adapt_response.json()

        return {
            "status": "success",
            "parsed_canonical_document": canonical_doc,
            "evaluation_result": evaluation_result,
            "final_declaration": final_declaration,
        }

    except httpx.HTTPStatusError as e:
        detail = f"Error from evaluation service: {e.response.text}"
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/ingestion-api")
async def health_check_ingestion_api():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{EVALUATION_SERVICE_URL}/health")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": e.response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}
