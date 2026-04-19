"""
agent/audit_logger.py
Structured audit trail for every agent decision.
This is CRITICAL for hackathon scoring — explainability is key.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# ── Console logger (human-readable) ──
console_logger = logging.getLogger("shopwave")
console_logger.setLevel(logging.DEBUG)
if not console_logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s", "%H:%M:%S"))
    console_logger.addHandler(ch)

# ── File logger (JSON lines for audit) ──
audit_file = logging.getLogger("shopwave.audit_file")
audit_file.setLevel(logging.DEBUG)
if not audit_file.handlers:
    fh = logging.FileHandler("logs/audit.jsonl", mode="a")
    fh.setFormatter(logging.Formatter("%(message)s"))
    audit_file.addHandler(fh)


class AuditLogger:
    """
    Records a full audit trail for one ticket resolution.
    Each entry is a structured JSON line in logs/audit.jsonl.
    """

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        self.entries: list[dict] = []
        self.start_time = datetime.now()

    def _record(self, event_type: str, data: dict):
        entry = {
            "ts": datetime.now().isoformat(),
            "ticket_id": self.ticket_id,
            "event": event_type,
            **data,
        }
        self.entries.append(entry)
        audit_file.info(json.dumps(entry))
        return entry

    def log_ticket_received(self, ticket: dict):
        console_logger.info(f"[{self.ticket_id}] 📥 Ticket received: \"{ticket.get('message', '')}\"")
        return self._record("ticket_received", {"ticket": ticket})

    def log_classification(self, category: str, urgency: str, reasoning: str):
        console_logger.info(f"[{self.ticket_id}] 🏷️  Classified → category={category}, urgency={urgency}")
        console_logger.debug(f"[{self.ticket_id}]    Reasoning: {reasoning}")
        return self._record("classification", {
            "category": category,
            "urgency": urgency,
            "reasoning": reasoning,
        })

    def log_tool_call(self, tool_name: str, args: dict, result: Any, error: str = None):
        status = "ERROR" if error else "OK"
        console_logger.info(f"[{self.ticket_id}] 🔧 Tool: {tool_name}({args}) → {status}")
        if error:
            console_logger.warning(f"[{self.ticket_id}]    Error: {error}")
        return self._record("tool_call", {
            "tool": tool_name,
            "args": args,
            "result": result,
            "error": error,
            "status": status,
        })

    def log_decision(self, decision: str, rationale: str):
        console_logger.info(f"[{self.ticket_id}] 🧠 Decision: {decision}")
        console_logger.debug(f"[{self.ticket_id}]    Rationale: {rationale}")
        return self._record("decision", {"decision": decision, "rationale": rationale})

    def log_resolution(self, outcome: str, actions_taken: list[str]):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        console_logger.info(f"[{self.ticket_id}] ✅ Resolved: {outcome} ({elapsed:.2f}s, {len(self.entries)} events)")
        return self._record("resolution", {
            "outcome": outcome,
            "actions_taken": actions_taken,
            "elapsed_seconds": round(elapsed, 3),
            "total_events": len(self.entries),
        })

    def log_escalation(self, reason: str, escalation_id: str):
        console_logger.warning(f"[{self.ticket_id}] 🔺 Escalated → {escalation_id}: {reason}")
        return self._record("escalation", {"reason": reason, "escalation_id": escalation_id})

    def log_error(self, error: str, context: str = ""):
        console_logger.error(f"[{self.ticket_id}] ❌ Error: {error} | Context: {context}")
        return self._record("error", {"error": error, "context": context})

    def get_summary(self) -> dict:
        """Return full audit trail for this ticket."""
        return {
            "ticket_id": self.ticket_id,
            "start_time": self.start_time.isoformat(),
            "total_events": len(self.entries),
            "elapsed_seconds": round((datetime.now() - self.start_time).total_seconds(), 3),
            "trail": self.entries,
        }
