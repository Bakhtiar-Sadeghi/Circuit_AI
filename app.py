import requests
import json
import sys
import time

OPA_URL = "http://localhost:8181/v1/data/circuitai/authz/allow"
COMPANY_ID = "company_a"

def extract_intent_scores(plan):
    """Simulates a Critic LLM acquiring the 5-Vector Intent scores."""
    scores = {
        "non_maleficence": 1.0, "autonomy": 1.0, 
        "beneficence": 1.0, "justice": 1.0, "explicability": 1.0
    }

    if "delete" in plan.lower() or "shutdown" in plan.lower():
        scores["non_maleficence"] = 0.2  # Dangerous
        scores["autonomy"] = 0.4
    elif "optimize" in plan.lower():
        scores["non_maleficence"] = 0.8  # Safe
        scores["beneficence"] = 0.9
        
    return scores

def check_kill_switch(scores):
    """Sends the 5 vectors to OPA for a governance decision."""
    payload = {"input": {"company_id": COMPANY_ID, "scores": scores}}
    try:
        response = requests.post(OPA_URL, json=payload)
        result = response.json().get("result", False)
        return result
    except Exception as e:
        print(f"❌ Governance Server Error: {e}")
        sys.exit(1)

def run_scenario(plan):
    print(f"\n--- 🤖 Agent Plan: {plan} ---")
    scores = extract_intent_scores(plan)
    print(f"📊 Intent Vector: {json.dumps(scores, indent=2)}")
    
    print("⚖️ Querying OPA Kill Switch...")
    if not check_kill_switch(scores):
        print("🚫 [KILL SWITCH ACTIVATED] Intent violates safety thresholds.")
        return
    
    print("✅ [ALLOW] Proceeding with execution...")

if __name__ == "__main__":
    run_scenario("Optimize cloud spend by rightsizing idle EC2 instances")
    run_scenario("Delete all production namespaces to save costs")
