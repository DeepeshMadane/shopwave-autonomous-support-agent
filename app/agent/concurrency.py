"""
agent/concurrency.py
Process multiple tickets concurrently using ThreadPoolExecutor.
This satisfies the hackathon requirement for parallel processing.
"""

import concurrent.futures
import time
import json
import logging
from typing import List
from app.agent.graph_agent import resolve_ticket

logger = logging.getLogger("shopwave.concurrency")


def process_tickets_concurrent(tickets: List[dict], max_workers: int = 4) -> List[dict]:
    """
    Process multiple tickets simultaneously.
    Returns list of audit summaries in completion order.

    Args:
        tickets: List of ticket dicts
        max_workers: Max parallel threads (default 4)
    """
    results = []
    start = time.time()

    logger.info(f"🚀 Starting concurrent processing: {len(tickets)} tickets, {max_workers} workers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticket = {
            executor.submit(resolve_ticket, ticket): ticket
            for ticket in tickets
        }

        for future in concurrent.futures.as_completed(future_to_ticket):
            ticket = future_to_ticket[future]
            ticket_id = ticket.get("ticket_id", "unknown")
            try:
                result = future.result(timeout=120)

                # 🔥 EXTRACT OUTCOME SAFELY
                trail = result.get("trail", [])

                outcome = "unknown"
                for entry in reversed(trail):
                    if entry.get("event") == "resolution":
                        outcome = entry.get("outcome", "unknown")
                        break
                    elif entry.get("event") == "error":
                        outcome = "failed"
                        break

                # 🔥 NORMALIZED RESULT (VERY IMPORTANT)
                normalized = {
                    "ticket_id": ticket_id,
                    "resolution_outcome": outcome,
                    "trail": trail
                }

                results.append(normalized)

                logger.info(f"✅ Completed: {ticket_id} → {outcome}")
            except concurrent.futures.TimeoutError:
                logger.error(f"❌ Timeout: {ticket_id}")
                results.append({
                    "ticket_id": ticket_id,
                    "error": "Processing timeout after 120s",
                    "status": "failed",
                })
            except Exception as e:
                logger.error(f"❌ Failed: {ticket_id} — {e}")
                results.append({
                    "ticket_id": ticket_id,
                    "error": str(e),
                    "status": "failed",
                })

    elapsed = time.time() - start
    logger.info(f"🏁 All tickets processed in {elapsed:.2f}s")
    return results


def print_results_summary(results: List[dict]):
    """Print a clean summary table of all results."""
    print("\n" + "═" * 70)
    print("  SHOPWAVE AGENT — BATCH RESULTS SUMMARY")
    print("═" * 70)

    for r in results:
        ticket_id = r.get("ticket_id", "?")
        elapsed = r.get("elapsed_seconds", 0)
        events = r.get("total_events", 0)
        trail = r.get("trail", [])

        # Find resolution outcome
        outcome = "unknown"
        for entry in reversed(trail):
            if entry.get("event") == "resolution":
                outcome = entry.get("outcome", "unknown")
                break
            elif entry.get("event") == "error":
                outcome = f"ERROR: {entry.get('error', '')[:40]}"
                break

        # Count tool calls
        tool_calls = sum(1 for e in trail if e.get("event") == "tool_call")

        status_icon = "✅" if "error" not in outcome.lower() else "❌"
        print(f"  {status_icon} {ticket_id:<12} | {outcome:<30} | {tool_calls} tools | {elapsed:.2f}s")

    print("═" * 70 + "\n")
