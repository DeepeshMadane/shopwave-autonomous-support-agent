# Failure Modes & Handling

## 1. API Rate Limits / Token Limits

* Cause: Large prompts or parallel calls
* Handling:

  * Reduced message context (last 3 messages)
  * Trimmed knowledge base content
  * Reduced concurrency (max_workers=2)

## 2. Invalid Tool Response

* Cause: Missing data or incorrect input
* Handling:

  * Safe parsing
  * Error logging
  * Continue or escalate

## 3. LLM Uncertainty

* Cause: Model does not call tools
* Handling:

  * Force minimum tool calls
  * Fallback decision

## 4. Refund Safety Violation

* Cause: Incorrect refund logic
* Handling:

  * Check refund status
  * Validate amount > 0
  * Block invalid refunds

## 5. System Failure

* Cause: Unexpected exception
* Handling:

  * try/catch in concurrency
  * return structured failure output
