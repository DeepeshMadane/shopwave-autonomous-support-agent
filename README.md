# 🛍️ ShopWave Autonomous Support Agent

### Hackathon Submission — LangGraph + Tool-Based AI Agent

---

## 🚀 Overview

An autonomous AI system that processes customer support tickets, uses tools, applies business logic, and resolves issues **without human intervention**.

---

## 🧠 Key Features

* 🔍 Ticket classification (category + urgency)
* 🧠 Autonomous reasoning using LLM + tools
* 🔧 Tool-based workflow (order, customer, KB)
* ⚡ Concurrent ticket processing
* 📊 Full audit trail (every decision logged)
* 🌐 Web UI with timeline visualization

---

## 🧱 Architecture

```
Incoming Ticket
      │
      ▼
┌─────────────┐
│   CLASSIFY  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   RESOLVE   │ ← LLM reasoning
└──────┬──────┘
       │ tool calls
       ▼
┌──────────────┐
│ TOOL EXECUTOR│
└──────────────┘
       │
       ▼
┌─────────────┐
│  FINALIZE   │
└─────────────┘
       │
       ▼
 AUDIT TRAIL (logs)
```

---

## 🔄 Workflow

1. Receive ticket
2. Classify (refund / delivery / issue)
3. Plan tool usage
4. Execute tools:

   * get_order
   * get_customer_by_email
   * search_knowledge_base
   * check_refund_eligibility
5. Take action:

   * send_reply
   * issue_refund
   * escalate_ticket
6. Log full audit trail

---

## ⚡ Concurrency

Tickets are processed in parallel using:

```
ThreadPoolExecutor(max_workers=2)
```

---

## 🌐 Web UI

* Interactive ticket selection
* Visual audit trail timeline
* Single + concurrent execution
* Clean step-by-step reasoning

---

## 🚀 Live Demo

👉 Trying to but time over sorry for this 

---

## ▶️ Run Locally

```
pip install -r requirements.txt
uvicorn app.api:app --reload
```

---

## ⚠️ Failure Modes & Handling

### 1. API Rate Limits / Token Limits

* Reduced context size
* Limited KB content
* Controlled concurrency

### 2. Invalid Tool Response

* Safe parsing
* Fallback handling
* Logged in audit trail

### 3. LLM Uncertainty

* Enforced tool usage
* Fallback decisions

### 4. Refund Safety

* Prevent duplicate refunds
* Validate amount > 0
* Check refund status

### 5. System Failures

* try/catch in concurrency
* structured failure response

---


