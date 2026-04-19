"""
agent/graph_agent.py
LangGraph-based autonomous support resolution agent.

Graph structure:
  START → classify → resolve → [send_reply | escalate] → END
                ↓ (tool loop)
           tool_executor → resolve (back)

Each node:
  - Has a clear single responsibility
  - Logs every step
  - Handles errors gracefully
  - Produces structured state updates
"""

import json
import re
import sys
import os
from typing import TypedDict, Annotated, List, Optional, Any
from datetime import datetime

# ── LangGraph imports ──
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

# ── LangChain / Anthropic ──
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool

# ── Internal imports ──
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools.api_tools import (
    get_order, get_customer, get_product,
    search_knowledge_base, check_refund_eligibility,
    issue_refund, send_reply, escalate
)
from agent.audit_logger import AuditLogger
from tools.api_tools import TOOL_MAP, ALL_TOOLS


import re

# ─────────────────────────────────────────────
# EXTRACTION + CONFIDENCE
# ─────────────────────────────────────────────

def extract_entities(text):
    order_match = re.search(r"ORD-\d+", text)
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)

    return {
        "order_id": order_match.group(0) if order_match else None,
        "email": email_match.group(0) if email_match else None
    }
def compute_confidence(state):
    score = 0.5

    if state.get("tool_calls_made", 0) >= 3:
        score += 0.2

    if state.get("extracted", {}).get("order_id"):
        score += 0.2

    if "error" not in str(state.get("actions_taken", [])):
        score += 0.1

    return min(score, 1.0)

# ─────────────────────────────────────────────
# NEW: PLANNING NODE
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    # Ticket input
    ticket_id: str
    ticket: dict

    # Classification output
    category: str
    urgency: str
    classification_reasoning: str

    # Conversation / tool messages
    messages: Annotated[List[Any], add_messages]

    # Resolution tracking
    tool_calls_made: int
    actions_taken: List[str]
    resolution_outcome: str
    resolved: bool
    should_escalate: bool
    escalation_reason: str

    # Audit
    audit: Any  # AuditLogger instance
def node_plan(state: AgentState) -> dict:
    ticket = state["ticket"]
    body = ticket.get("body", "")

    entities = extract_entities(body)

    plan = []
    if entities["order_id"]:
        plan.append("get_order")

    plan.append("get_customer_by_email")
    plan.append("search_knowledge_base")

    state["plan"] = plan
    state["extracted"] = entities

    state["audit"].log_decision(
        decision="Planning step",
        rationale=f"Plan={plan}, Extracted={entities}"
    )

    return state





# ─────────────────────────────────────────────
# LangChain Tool Wrappers
# ─────────────────────────────────────────────

@tool
def tool_get_order(order_id: str) -> str:
    """Fetch order details by order ID."""
    try:
        result = get_order(order_id)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "retry": True})

@tool
def tool_get_customer(customer_id: str) -> str:
    """Fetch customer profile by customer ID."""
    try:
        result = get_customer(customer_id)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "retry": True})

@tool
def tool_get_product(product_id: str) -> str:
    """Fetch product details by product ID."""
    try:
        result = get_product(product_id)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "retry": True})

@tool
def tool_search_knowledge_base(query: str) -> str:
    """Search internal knowledge base for policies and FAQs."""
    try:
        result = search_knowledge_base(query)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_check_refund_eligibility(order_id: str) -> str:
    """Check whether an order is eligible for a refund."""
    try:
        result = check_refund_eligibility(order_id)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_issue_refund(order_id: str, amount: float, reason: str) -> str:
    """Issue a refund to the customer for a given order."""
    try:
        result = issue_refund(order_id, amount, reason)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_send_reply(customer_email: str, subject: str, body: str) -> str:
    """Send an email reply to the customer."""
    try:
        result = send_reply(customer_email, subject, body)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_escalate(ticket_id: str, summary: str, priority: str, reason: str) -> str:
    """Escalate a ticket to a human agent."""
    try:
        result = escalate(ticket_id, summary, priority, reason)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_get_customer_by_email(email: str) -> str:
    """Fetch customer profile using email address."""
    try:
        from tools.api_tools import get_customer_by_email
        result = get_customer_by_email(email)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

# ALL_TOOLS = [
#     tool_get_order, tool_get_customer, tool_get_product,
#     tool_search_knowledge_base, tool_check_refund_eligibility,
#     tool_issue_refund, tool_send_reply, tool_escalate,
#     tool_get_customer_by_email
# ]

# TOOL_MAP = {t.name: t for t in ALL_TOOLS}
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

# ✅ Load .env FIRST
load_dotenv()

# ✅ Correct env variable name
groq_api_key = os.getenv("GROQ_API_KEY")

# 🚨 Safety check (VERY IMPORTANT)
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found. Check your .env file")

# ─────────────────────────────────────────────
# LLM SETUP
# ─────────────────────────────────────────────

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="llama-3.1-8b-instant",
    temperature=0   # 👈 better for tool usage
)

llm_with_tools = llm.bind_tools(
    ALL_TOOLS,
    tool_choice="auto"
)
# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are ShopWave's Autonomous Support Agent.

Your job is to resolve customer support tickets accurately using tools.

---

WORKFLOW:

1. Extract key details (order_id, email, issue type)
2. Call get_order(order_id) if available
3. Call get_customer_by_email(email)
4. Call search_knowledge_base for policy

---

DECISION RULES:

- Refund requests:
  → Check order refund_status FIRST
  → If already refunded → DO NOT issue refund → inform customer
  → If not refunded → check eligibility → then issue_refund

- Delivery issues:
  → Check delivery status → respond accordingly

- Damaged/defective:
  → Check eligibility → refund or replacement

- Wrong item / wrong size delivered:
  → IGNORE return window
  → Offer exchange OR refund
  → DO NOT deny based on eligibility
  → Prefer exchange if possible

- Unknown/complex:
  → escalate_ticket

---

ESCALATION RULES (STRICT):

- Use ONLY escalate_ticket tool
- Required parameters:
  → ticket_id
  → summary
  → priority
  → reason
- DO NOT pass customer_id or unsupported fields

---

CRITICAL RULES:

- NEVER issue refund if refund_status = "refunded"
- NEVER issue refund with amount <= 0
- ALWAYS verify using tools before decision
- DO NOT call the same tool twice if data already exists
- NEVER assume facts not present in tool data
- DO NOT call unnecessary tools
- STOP after completing the correct final action

---

FINAL ACTION RULE:

You MUST end with exactly ONE of:
→ send_reply
→ issue_refund
→ escalate_ticket

Do NOT perform multiple final actions.

---

OUTPUT BEHAVIOR:

- Be precise and deterministic
- Avoid repeated tool calls
- Do not loop
- Prefer informing the user over taking incorrect action
"""

# ─────────────────────────────────────────────
# GRAPH NODES
# ─────────────────────────────────────────────

def node_classify(state: AgentState) -> dict:
    """
    Node 1: Classify the incoming ticket.
    Determines category and urgency without tool calls.
    """
    audit: AuditLogger = state["audit"]
    ticket = state["ticket"]
    message = ticket.get("body", "")

    classify_prompt = f"""Classify this customer support ticket. Respond in JSON only.

Ticket: "{message}"

Respond with this exact JSON:
{{
  "category": "<one of: refund|delivery|damaged|address_change|cancellation|other>",
  "urgency": "<one of: high|medium|low>",
  "reasoning": "<1-2 sentence explanation>"
}}"""

    response = llm.invoke([HumanMessage(content=classify_prompt)])
    raw = response.content.strip()

    # Parse JSON safely
    try:
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
        parsed = json.loads(clean)
    except Exception:
        parsed = {"category": "other", "urgency": "medium", "reasoning": "Could not parse classification"}

    category = parsed.get("category", "other")
    urgency = parsed.get("urgency", "medium")
    reasoning = parsed.get("reasoning", "")

    audit.log_ticket_received(ticket)
    audit.log_classification(category, urgency, reasoning)

    return {
        "category": category,
        "urgency": urgency,
        "classification_reasoning": reasoning,
        "messages": [SystemMessage(content=SYSTEM_PROMPT)],
    }

import re

def extract_order_id(text):
    match = re.search(r"ORD-\d+", text)
    return match.group(0) if match else None


def node_resolve(state: AgentState) -> dict:
    audit = state["audit"]
    ticket = state["ticket"]

    # 🔴 1. STOP if already resolved
    if state.get("resolution_outcome"):
        return {}

    # 🔴 2. ITERATION CONTROL
    state["iteration"] = state.get("iteration", 0) + 1

    if state["iteration"] > 4:
        audit.log_decision(
            decision="Max iterations reached",
            rationale="Stopping to prevent infinite loop"
        )
        return {
            "resolution_outcome": "stopped_due_to_limit"
        }

    body = ticket.get("body", "")
    extracted = state.get("extracted", {})

    order_id = extracted.get("order_id")
    email = extracted.get("email") or ticket.get("customer_email")

    # 🔴 3. REDUCE TOKEN USAGE
    base_messages = state["messages"][-3:] if state["messages"] else []

    # 🔥 4. BUILD SMART CONTEXT
    context = f"""
Ticket: {ticket['ticket_id']}
Email: {email}
Order: {order_id}

Message: {body}

Plan: {state.get("plan")}

STRICT INSTRUCTIONS:
- Follow plan step-by-step
- Do NOT call the same tool twice
- If order_data already exists → DO NOT call get_order again
- If customer data exists → DO NOT call get_customer again
- NEVER assume facts not in tool data
- STOP after final action
"""

    # 🔥 ADD MEMORY AWARENESS
    if state.get("order_data"):
        context += "\nNOTE: Order data already retrieved. Do NOT call get_order again.\n"

    if state.get("customer_data"):
        context += "\nNOTE: Customer data already retrieved. Do NOT call get_customer again.\n"

    if state["tool_calls_made"] == 0:
        messages = base_messages + [HumanMessage(content=context)]
    else:
        # still reinforce rules even after first step
        messages = base_messages + [HumanMessage(content="Continue reasoning. Do not repeat tools.")]

    # 🔴 5. LLM CALL
    response = llm_with_tools.invoke(messages)

    # 🔴 6. LOG DECISION
    audit.log_decision(
        decision=f"Agent response (tool_calls={len(getattr(response,'tool_calls',[]))})",
        rationale=response.content[:200] if response.content else "tool execution"
    )

    # 🔴 7. STOP IF NO TOOL CALLS (FINAL ANSWER)
    if not getattr(response, "tool_calls", []):
        return {
            "messages": [response],
            "resolution_outcome": "completed"
        }

    return {
        "messages": [response]
    }

from utils.retry import retry
def node_tool_executor(state: AgentState) -> dict:
    """
    Node 3: Execute all tool calls from the agent's last message.
    Handles errors, retries, business logic validation, memory, and stopping conditions.
    """
    audit: AuditLogger = state["audit"]
    last_message = state["messages"][-1]
    ticket = state.get("ticket", {})

    # 🚨 SAFETY: no tool calls → finalize
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        audit.log_decision(
            decision="No tool calls from LLM",
            rationale="LLM returned no tool_calls — moving to finalize"
        )
        return {
            "messages": [],
            "resolution_outcome": "completed"
        }

    tool_results = []
    actions_taken = state.get("actions_taken", [])
    tool_calls_made = state.get("tool_calls_made", 0)

    final_action_detected = False

    for tc in last_message.tool_calls:
        tool_name = tc.get("name")
        args = tc.get("args", {})
        tool_id = tc.get("id")
        # 🔥 FORCE RESPONSE FIX (VERY IMPORTANT)
        if tool_name == "send_reply" and state.get("forced_reply"):
            args["body"] = (
                "Dear customer,\n\n"
                "We have reviewed your request and unfortunately the order is outside "
                "the return window, so a refund cannot be processed.\n\n"
                "However, we can assist you further if needed.\n\n"
                "Best regards,\nShopWave Support"
            )

        # 🔥 PREVENT DUPLICATE TOOL CALLS
        if tool_name == "get_order" and state.get("order_data"):
            audit.log_decision("Skipping get_order", "Order already fetched")
            continue

        if tool_name in ["get_customer", "get_customer_by_email"] and state.get("customer_data"):
            audit.log_decision("Skipping get_customer", "Customer already fetched")
            continue

        try:
            tool_fn = TOOL_MAP.get(tool_name)

            if not tool_fn:
                parsed_result = {"error": f"Unknown tool: {tool_name}"}
            else:
                result = retry(lambda: tool_fn(**args))

                if isinstance(result, str):
                    try:
                        parsed_result = json.loads(result)
                    except Exception:
                        parsed_result = {"raw_output": result}
                else:
                    parsed_result = result

            # 🔥 STORE ORDER DATA
            if tool_name == "get_order" and parsed_result.get("success"):
                state["order_data"] = parsed_result.get("data", {})

            # 🔥 STORE CUSTOMER DATA
            if tool_name in ["get_customer", "get_customer_by_email"] and parsed_result.get("success"):
                state["customer_data"] = parsed_result.get("data", {})

            # 🔥 STORE ELIGIBILITY (MISSING FIX)
            if tool_name == "check_refund_eligibility":
                state["refund_eligibility"] = parsed_result

            # 🔥 BUSINESS LOGIC: DEFECT DETECTION
            body_lower = ticket.get("body", "").lower()

            is_defective = any(word in body_lower for word in [
                "defect", "not working", "broken", "damaged", "stopped working"
            ])

            # 🔥 BLOCK INVALID REFUND
            if tool_name == "issue_refund":
                order_data = state.get("order_data", {})
                eligibility = state.get("refund_eligibility", {})

                # 🚫 Already refunded
                if order_data.get("refund_status") == "refunded":
                    audit.log_decision("Skipping refund", "Already refunded")
                    continue

                # 🔥 HARD BLOCK (FINAL FIX)
                if "eligible" in eligibility and not eligibility["eligible"]:
                    audit.log_decision(
                        decision="Blocking refund",
                        rationale=f"Refund not eligible → {eligibility}"
                    )

                    state["forced_reply"] = {"type": "refund_denied"}

                    continue

                # 🚫 invalid amount
                if args.get("amount", 0) <= 0:
                    audit.log_decision("Skipping refund", "Invalid amount")
                    continue

            error = parsed_result.get("error") if isinstance(parsed_result, dict) else None
            if error:
                audit.log_decision("Tool failure", error)

            audit.log_tool_call(tool_name, args, parsed_result, error=error)

            actions_taken.append(f"{tool_name}({args})")
            tool_calls_made += 1

            # 🔥 FINAL ACTION DETECTION
            if tool_name in ["send_reply", "issue_refund", "tool_escalate", "escalate"]:
                final_action_detected = True

        except Exception as e:
            error_msg = str(e)
            audit.log_tool_call(tool_name, args, None, error=error_msg)

            parsed_result = {
                "error": error_msg,
                "recovered": True
            }

        tool_results.append(
            ToolMessage(
                content=json.dumps(parsed_result),
                tool_call_id=tool_id
            )
        )

    # 🔥 STOP AFTER FINAL ACTION
    if final_action_detected:
        audit.log_decision("Final action executed", "Stopping execution")

        return {
            "messages": tool_results,
            "tool_calls_made": tool_calls_made,
            "actions_taken": actions_taken,
            "resolution_outcome": "completed"
        }

    return {
        "messages": tool_results,
        "tool_calls_made": tool_calls_made,
        "actions_taken": actions_taken,
    }
def node_finalize(state: AgentState) -> dict:
    audit = state["audit"]

    actions = state.get("actions_taken", [])
    order_data = state.get("order_data", {})

    # 🔥 1. BUSINESS LOGIC FIRST (MOST IMPORTANT)
    if order_data.get("refund_status") == "refunded":
        outcome = "refund_already_processed"

    # 🔥 2. ACTION-BASED LOGIC
    elif any("issue_refund" in a for a in actions):
        outcome = "refund_issued"

    elif any("escalate" in a for a in actions):
        outcome = "escalated_to_human"

    elif any("send_reply" in a for a in actions):
        outcome = "responded"

    else:
        outcome = "resolved_autonomously"

    # 🔥 3. CONFIDENCE CHECK (AFTER LOGIC)
    confidence = compute_confidence(state)

    if confidence < 0.6:
        audit.log_decision(
            decision="Escalation",
            rationale=f"Low confidence: {confidence}"
        )
        outcome = "escalated_low_confidence"

    # 🔥 LOG FINAL RESULT
    
    if state.get("forced_reply"):
        outcome = "responded"
    audit.log_resolution(outcome, actions)

    return {
        "resolution_outcome": outcome,
        "resolved": True,
    }

# ─────────────────────────────────────────────
# ROUTING LOGIC
# ─────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    if state.get("resolution_outcome"):
        return "finalize"

    last_message = state["messages"][-1]
    tool_calls_made = state.get("tool_calls_made", 0)
    if tool_calls_made < 3:
        return "tool_executor"

    if tool_calls_made >= 5:
        return "finalize"

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_executor"

    return "finalize"

# ─────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("plan", node_plan)
    graph.add_node("classify", node_classify)
    graph.add_node("resolve", node_resolve)
    graph.add_node("tool_executor", node_tool_executor)
    graph.add_node("finalize", node_finalize)

    # Entry
    graph.set_entry_point("plan")

    # Flow
    graph.add_edge("plan", "classify")
    graph.add_edge("classify", "resolve")

    # 🔥 KEY DECISION POINT
    graph.add_conditional_edges(
        "resolve",
        should_continue,
        {
            "tool_executor": "tool_executor",
            "finalize": "finalize",
        }
    )

    # Loop
    graph.add_edge("tool_executor", "resolve")

    # End
    graph.add_edge("finalize", END)

    return graph.compile()


GRAPH = build_graph()
# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def resolve_ticket(ticket: dict) -> dict:
    """
    Main entry point. Takes a ticket dict, runs the full agent graph.
    Returns audit summary with outcome.
    """
    ticket_id = ticket.get("ticket_id", f"T-{int(datetime.now().timestamp())}")
    audit = AuditLogger(ticket_id)

    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "ticket": ticket,
        "category": "",
        "urgency": "",
        "classification_reasoning": "",
        "messages": [],
        "tool_calls_made": 0,
        "actions_taken": [],
        "resolution_outcome": "",
        "resolved": False,
        "should_escalate": False,
        "escalation_reason": "",
        "audit": audit,
        "refund_eligibility": {},
        "order_data": {},
        "customer_data": {},
    }

    final_state = GRAPH.invoke(initial_state)
    return audit.get_summary()
