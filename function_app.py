import azure.functions as func
from datetime import datetime, timezone
import json
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Literal
from lib.llm_client import call_llm

app = func.FunctionApp()

# Constants
MIMETYPE_JSON = "application/json"

def load_system_prompt() -> str:
    """Load the system prompt from a file."""
    prompt_path = Path(__file__).parent / "prompts" / "incident_triage_system_v1.txt"
    with open(prompt_path, 'r') as f:
        return f.read()

# Pydantic model for incident output validation
class IncidentOutput(BaseModel):
    incident_id: str = Field(..., min_length=1, description="Unique incident identifier")
    incident_summary: str = Field(..., min_length=1, description="Brief summary of the incident")
    description: str = Field(..., min_length=1, description="Detailed incident description")
    primary_signals: list[str] = Field(..., description="List of primary signals detected")
    risks_or_unknowns: list[str] = Field(default_factory=list, description="List of risks or unknowns")
    triage_outcome: Literal["action_required", "needs_clarification", "monitor_only", 
                            "false_positive", "duplicate_or_known"]
    severity: Literal["Sev0", "Sev1", "Sev2", "Sev3", "Sev4"]
    urgency: Literal["Low", "Medium", "High", "Critical"]
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp_format(cls, v: str) -> str:
        """Validate timestamp is in ISO 8601 format"""
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Invalid timestamp format - must be ISO 8601")
        return v
    
    @field_validator('primary_signals')
    @classmethod
    def validate_primary_signals_not_empty(cls, v: list[str], info) -> list[str]:
        """Ensure primary_signals is not empty when triage_outcome is action_required"""
        triage_outcome = info.data.get('triage_outcome')
        if triage_outcome == 'action_required' and not v:
            raise ValueError("primary_signals must not be empty when triage_outcome is action_required")
        return v
    
# # --- Post-Run Eval ---
def validate_incident_output(output) -> dict:
    """Validate incident output using Pydantic model"""
    try:
        IncidentOutput(**output)
        return {"hard_fail": False, "errors": []}
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        return {"hard_fail": True, "errors": errors}
    except Exception as e:
        return {"hard_fail": True, "errors": [f"Validation error: {str(e)}"]}

def run_agent_core(input_text: str, run_id: str | None = None) -> dict:
    if run_id is None:
        run_id = str(uuid.uuid4())

    logging.info(f"[{run_id}] Stage=receive_input length={len(input_text)}")

    # --- Pre-Run Eval ---
    if not input_text.strip():
        raise ValueError("Empty input")

    # --- Planning ---
    plan = [
        "Read input",
        "Extract key points",
        "Identify risks or gaps",
        "Format JSON output"
    ]

    if len(plan) > 10:
        raise RuntimeError("Plan too long")

    system_prompt = load_system_prompt()
    message = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": input_text}
    ]
    # --- Execution (Incident Triage Stub) ---
    raw_output = call_llm(message, temperature=0, max_tokens=1500)
    try:
        logging.info(f"[{run_id}] Stage=llm_call length={len(raw_output)}")
        output = json.loads(raw_output)
        output["timestamp"] = datetime.now(timezone.utc).isoformat()
    except json.JSONDecodeError:
        raise ValueError("LLM output is not valid JSON")
    return output

@app.route(route="agent_runner", auth_level=func.AuthLevel.FUNCTION)
def agent_runner(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        input_text = req_body.get("input_text", "")
        result = run_agent_core(input_text)
        validation_result = validate_incident_output(result)
        
        if validation_result["hard_fail"]:
            return func.HttpResponse(
                json.dumps({"error": "Output validation failed", "details": validation_result["errors"]}),
                status_code=500,
                mimetype=MIMETYPE_JSON
            )
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype=MIMETYPE_JSON
        )
    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=400,
            mimetype=MIMETYPE_JSON
        )
    except Exception as e:
        logging.exception("Unhandled error")
        return func.HttpResponse(
            json.dumps({"error": "Internal error"}),
            status_code=500,
            mimetype=MIMETYPE_JSON
        )

