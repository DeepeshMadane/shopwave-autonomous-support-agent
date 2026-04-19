import json
import os

BASE_PATH = os.path.join(os.path.dirname(__file__), "raw")

def load_json(file_name):
    with open(os.path.join(BASE_PATH, file_name)) as f:
        return json.load(f)

def load_customers():
    return load_json("customers.json")

def load_orders():
    return load_json("orders.json")

def load_products():
    return load_json("products.json")

def load_tickets():
    return load_json("tickets.json")

def load_knowledge_base():
    with open(os.path.join(BASE_PATH, "knowledge-base.md")) as f:
        return f.read()