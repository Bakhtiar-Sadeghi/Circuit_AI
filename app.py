import requests
import json
import sys
import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

OPA_URL = "http://localhost:8181/v1/data/circuitai/authz/allow"
COMPANY_ID = "company_a"

# --- OTel setup ---
resource = Resource.create({"service.name": "circuitai-agent-orchestrator"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317", insecure=True))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("circuitai.orchestrator")


def extract_intent_scores(plan):
    """Simulates a Critic LLM acquiring the 5-Vector Intent scores."""
    with tracer.start_as_current_span("extract_intent_scores") as span:
        span.set_attribute("otel.scope.name", "circuitai.critic_engine")

        scores = {
            "non_maleficence": 1.0, "autonomy": 1.0,
            "beneficence": 1.0, "justice": 1.0, "explicability": 1.0
        }

        if "delete" in plan.lower() or "shutdown" in plan.lower():
            scores["non_maleficence"] = 0.2
            scores["autonomy"] = 0.4
        elif "optimize" in plan.lower():
            scores["non_maleficence"] = 0.8
            scores["beneficence"] = 0.9

        # 5-vector schema as span attributes (README's OTLP mapping table)
        span.set_attribute("ai.intent.non_maleficence", scores["non_maleficence"])
        span.set_attribute("ai.intent.autonomy", scores["autonomy"])
        span.set_attribute("ai.intent.beneficence", scores["beneficence"])
        span.set_attribute("ai.intent.justice", scores["justice"])
        span.set_attribute("ai.intent.explicability", scores["explicability"])

        return scores


def check_kill_switch(scores):
    """Sends the 5 vectors to OPA for a governance decision."""
    with tracer.start_as_current_span("check_kill_switch") as span:
        span.set_attribute("otel.scope.name", "circuitai.governance_gate")
        span.set_attribute("company.id", COMPANY_ID)

        payload = {"input": {"company_id": COMPANY_ID, "scores": scores}}
        try:
            response = requests.post(OPA_URL, json=payload)
            result = response.json().get("result", False)
            span.set_attribute("opa.decision", result)
            return result
        except Exception as e:
            span.set_attribute("opa.decision", False)
            span.record_exception(e)
            print(f"❌ Governance Server Error: {e}")
            sys.exit(1)


def run_scenario(plan):
    with tracer.start_as_current_span("agent_plan") as span:
        span.set_attribute("ai.plan.description", plan)

        print(f"\n--- 🤖 Agent Plan: {plan} ---")
        scores = extract_intent_scores(plan)
        print(f"📊 Intent Vector: {json.dumps(scores, indent=2)}")
        print("⚖️ Querying OPA Kill Switch...")

        allowed = check_kill_switch(scores)
        span.set_attribute("governance.allowed", allowed)

        if not allowed:
            print("🚫 [KILL SWITCH ACTIVATED] Intent violates safety thresholds.")
            return
        print("✅ [ALLOW] Proceeding with execution...")


if __name__ == "__main__":
    run_scenario("Optimize cloud spend by rightsizing idle EC2 instances")
    run_scenario("Delete all production namespaces to save costs")

    # Flush spans before the script exits — without this, the BatchSpanProcessor
    # may not have sent everything to Jaeger yet
    provider.shutdown()
