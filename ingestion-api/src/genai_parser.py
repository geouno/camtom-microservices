import os
import json
from google.genai import Client, types
from .canonical_models import CanonicalDocument

GENAI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """
You are an expert customs document parser. Your task is to extract structured data from the provided document and return a single, valid JSON object that strictly conforms to the provided schema.

Rules:
- Do NOT invent data. If a field is not present, use an empty string "" or 0.
- For items, `hs_code` should be the 6-digit universal code. National extensions (like Mexico's NICO) should be placed in the `extensions` object (e.g., `"extensions": {"MX_NICO": "01"}`).
- Ensure all monetary values are numbers (float), not strings.
- Never include comments, markdown formatting (like ```json), or trailing commas in your output.
- "jurisdiction" field depends on the destination country e.g MX, BR, etc.
"""


def parse_image_to_canonical(
    pdf_bytes: bytes, org_id: str, jurisdiction: str
) -> CanonicalDocument:
    api_key = os.environ.get("GOOGLE_GENAI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_GENAI_API_KEY environment variable not set.")

    client = Client(api_key=api_key)
    schema_dict = CanonicalDocument.model_json_schema()
    # Remove the 'org_id' field from the schema
    schema_dict["properties"].pop("org_id")
    if "required" in schema_dict:
        schema_dict["required"].remove("org_id")
    print(schema_dict)
    schema_json = json.dumps(schema_dict, indent=2)
    print(schema_json)

    # gemini does not support pydantic models hehe
    # TODO: Fix this
    prompt = f"{SYSTEM_PROMPT}\n\nTarget JSON Schema:\n{schema_json}\n\nParse the following image document."

    # NOTE: The library name changed from google.genai to google.generativeai
    # This code uses the latter, which is the current standard.
    response = client.models.generate_content(
        model=GENAI_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=pdf_bytes, mime_type="image/png"),
        ],
        config={
            "response_mime_type": "application/json",
            # "response_schema": schema_dict,
        },
    )

    text = getattr(response, "text", None)
    if text is None or not isinstance(text, str) or not text.strip():
        raise ValueError(
            f"Failed to generate content from Gemini response: {response.text}"
        )

    try:
        print("Gemini response:", text)
        parsed_data = json.loads(text)
        # Example population of platform-specific fields
        parsed_data["org_id"] = org_id
        parsed_data["jurisdiction"] = jurisdiction
        return CanonicalDocument(**parsed_data)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(
            f"Failed to parse valid JSON from Gemini response: {response.text}"
        ) from e
