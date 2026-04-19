def load_tickets(path="data/tickets.json"):
    import json
    with open(path) as f:
        return json.load(f)
