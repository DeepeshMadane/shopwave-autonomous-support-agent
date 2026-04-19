from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.agent.concurrency import process_tickets_concurrent
from app.agent.graph_agent import resolve_ticket
from app.data.loader import load_tickets

app = FastAPI()

# Static + templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# 🏠 UI Route
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    raw_tickets = load_tickets()

    tickets = [
        {
            "ticket_id": t["ticket_id"],
            "body": t["body"]
        }
        for t in raw_tickets
    ]

    return templates.TemplateResponse(
        request,          # ✅ FIRST ARG (VERY IMPORTANT)
        "index.html",     # ✅ SECOND
        {
            "request": request,
            "tickets": tickets
        }
    )
    # return templates.TemplateResponse(
    #     "index.html",
    #     {
    #         "request": request,
    #         "tickets": tickets
    #     }
    # )


# 🚀 Run Agent
@app.post("/run")
async def run_agent(request: Request):
    try:
        data = await request.json()
        ticket_id = data.get("ticket_id")

        tickets = load_tickets()
        ticket = next(t for t in tickets if t["ticket_id"] == ticket_id)

        result = resolve_ticket(ticket)
        print("FINAL RESULT:", result)
        return {
            "outcome": result.get("resolution_outcome") 
                    or result.get("outcome") 
                    or "unknown",
            "trail": result.get("trail", [])
        }

    except Exception as e:
        return {
            "outcome": "failed",
            "error": str(e)
        }

@app.post("/run_all")
async def run_all():
    tickets = load_tickets()
    results = process_tickets_concurrent(tickets, max_workers=2)

    return [
        {
            "ticket_id": r.get("ticket_id"),
            "resolution_outcome": r.get("resolution_outcome")
        }
        for r in results
    ]