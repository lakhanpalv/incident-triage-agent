import azure.functions as func
import datetime
import json
import logging
import uuid

app = func.FunctionApp()

# Constants
MIMETYPE_JSON = "application/json"

# # --- Post-Run Eval ---
def validate_incident_output(output) -> dict:
    errors = []

    if not isinstance(output, dict):
        errors.append("Output is not a dict")

    if "incident_id" not in output or not isinstance(output["incident_id"], str):
        errors.append("Missing or invalid incident_id")

    if "incident_summary" not in output or not isinstance(output["incident_summary"], str):
        errors.append("Missing or invalid incident_summary")
    elif not output["incident_summary"].strip():
        errors.append("incident_summary is empty")

    if "description" not in output or not isinstance(output["description"], str):
        errors.append("Missing or invalid description")

    if "triage_outcome" not in output or output["triage_outcome"] not in ["action_required", "needs_clarification", "monitor_only", "false_positive", "duplicate_or_known"]:
        errors.append("Missing or invalid triage_outcome")

    if "primary_signals" not in output or not isinstance(output["primary_signals"], list):
        errors.append("Missing or invalid primary_signals")
    elif output.get("triage_outcome") == "action_required" and not output["primary_signals"]:
        errors.append("primary_signals must not be empty when triage_outcome is action_required")

    if "severity" not in output or output["severity"] not in ["Sev0", "Sev1", "Sev2", "Sev3", "Sev4"]:
        errors.append("Missing or invalid severity")

    if "urgency" not in output or output["urgency"] not in ["Low", "Medium", "High", "Critical"]:
        errors.append("Missing or invalid urgency")

    if "timestamp" not in output:
        errors.append("Missing timestamp")
    else:
        try:
            datetime.datetime.fromisoformat(output["timestamp"])
        except ValueError:
            errors.append("Invalid timestamp format")

    return {
        "hard_fail": len(errors) > 0,
        "errors": errors
    }

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

    # --- Execution (Incident Triage Stub) ---
    output = {
        "incident_id": run_id,
        "incident_summary": "Users experiencing login failures across mobile app",
        "description": input_text,
        "primary_signals": [
            "Login failures reported",
            "Authentication service unavailable",
            "Multiple regions affected"
        ],
        "risks_or_unknowns": [],
        "triage_outcome": "action_required",
        "severity": "Sev3",
        "urgency": "High",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
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

