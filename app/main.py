"""
main.py — ShopWave Autonomous Support Resolution Agent
LangGraph + Claude | Hackathon Submission
"""

import json
import argparse
import logging

from app.agent.graph_agent import resolve_ticket
from app.agent.concurrency import process_tickets_concurrent
from data.loader import load_tickets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# ─────────────────────────────────────────────
# HELPER: PRINT SUMMARY (FIXED)
# ─────────────────────────────────────────────

def print_results_summary(results):
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS SUMMARY")
    print("=" * 50)

    total = len(results)
    resolved = sum(1 for r in results if r.get("resolution_outcome") == "resolved_autonomously")
    escalated = sum(1 for r in results if "escalated" in r.get("resolution_outcome", ""))

    print(f"Total Tickets : {total}")
    print(f"Resolved      : {resolved}")
    print(f"Escalated     : {escalated}")
    print("=" * 50 + "\n")


# ─────────────────────────────────────────────
# SINGLE RUN
# ─────────────────────────────────────────────

def run_single(ticket_id: str = "TKT-001"):
    tickets = load_tickets()
    ticket = next((t for t in tickets if t["ticket_id"] == ticket_id), tickets[0])

    print(f"\n{'═'*70}")
    print(f"  SINGLE TICKET DEMO — {ticket['ticket_id']}")
    print(f"  Message: \"{ticket['body']}\"")
    print(f"{'═'*70}\n")

    result = resolve_ticket(ticket)

    print(f"\n{'─'*70}")
    print("  AUDIT TRAIL")
    print(f"{'─'*70}")

    for entry in result["trail"]:
        event = entry["event"]
        ts = entry["ts"][11:19]

        if event == "ticket_received":
            print(f"[{ts}] 📥 TICKET RECEIVED")

        elif event == "classification":
            print(f"[{ts}] 🏷️ CLASSIFY → {entry['category']} | urgency={entry['urgency']}")
            print(f"       {entry['reasoning']}")

        elif event == "tool_call":
            status = "✅" if entry["status"] == "OK" else "❌"
            print(f"[{ts}] 🔧 {status} {entry['tool']}({json.dumps(entry['args'])})")

        elif event == "decision":
            print(f"[{ts}] 🧠 {entry['decision']}")

        elif event == "resolution":
            print(f"[{ts}] 🎯 OUTCOME: {entry['outcome']}")

        elif event == "escalation":
            print(f"[{ts}] 🔺 ESCALATED: {entry['reason']}")

        elif event == "error":
            print(f"[{ts}] ❌ ERROR: {entry['error']}")

    print(f"{'═'*70}\n")
    return result


# ─────────────────────────────────────────────
# BATCH RUN
# ─────────────────────────────────────────────

def run_batch():
    print(f"\n{'═'*70}")
    print("  SHOPWAVE AUTONOMOUS SUPPORT AGENT")
    print("  Batch Mode — Processing all tickets concurrently")
    print(f"{'═'*70}\n")

    tickets = load_tickets()
    results = process_tickets_concurrent(tickets, max_workers=4)

    print_results_summary(results)

    with open("logs/batch_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("📄 Full audit saved to logs/batch_results.json\n")
    return results


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShopWave Autonomous Support Agent")
    parser.add_argument("--single", action="store_true", help="Process one ticket")
    parser.add_argument("--ticket", type=str, help="Ticket ID (e.g. TKT-002)")
    args = parser.parse_args()

    if args.single:
        run_single("TKT-001")
    elif args.ticket:
        run_single(args.ticket)
    else:
        run_batch()