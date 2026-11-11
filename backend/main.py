"""SmartDesk - mini CRM de relation client avec assistant IA."""
import json, os, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SmartDesk API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL, company TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS tickets(
  id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL REFERENCES customers(id),
  subject TEXT NOT NULL, message TEXT NOT NULL, status TEXT DEFAULT 'nouvelle',
  priority TEXT DEFAULT 'normale', topic TEXT DEFAULT '', ai_reply TEXT DEFAULT '', created_at TEXT);
"""
STATUSES = {"nouvelle", "en_cours", "resolue"}


@contextmanager
def db():
    con = sqlite3.connect(os.getenv("DB_PATH", "smartdesk.db"))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


class CustomerIn(BaseModel):
    name: str
    email: str
    company: str = ""


class TicketIn(BaseModel):
    customer_id: int
    subject: str
    message: str


class TicketPatch(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None


# ---------- Clients (CRUD) ----------
@app.post("/customers", status_code=201)
def create_customer(c: CustomerIn):
    with db() as con:
        cur = con.execute("INSERT INTO customers(name,email,company) VALUES(?,?,?)", (c.name, c.email, c.company))
        return {"id": cur.lastrowid, **c.model_dump()}


@app.get("/customers")
def list_customers():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM customers ORDER BY id DESC")]


@app.get("/customers/{cid}")
def get_customer(cid: int):
    with db() as con:
        row = con.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "Client introuvable")
    return dict(row)


@app.put("/customers/{cid}")
def update_customer(cid: int, c: CustomerIn):
    with db() as con:
        cur = con.execute("UPDATE customers SET name=?,email=?,company=? WHERE id=?", (c.name, c.email, c.company, cid))
    if cur.rowcount == 0:
        raise HTTPException(404, "Client introuvable")
    return {"id": cid, **c.model_dump()}


@app.delete("/customers/{cid}", status_code=204)
def delete_customer(cid: int):
    with db() as con:
        con.execute("DELETE FROM tickets WHERE customer_id=?", (cid,))
        cur = con.execute("DELETE FROM customers WHERE id=?", (cid,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Client introuvable")


# ---------- Demandes ----------
@app.post("/tickets", status_code=201)
def create_ticket(t: TicketIn):
    with db() as con:
        if not con.execute("SELECT 1 FROM customers WHERE id=?", (t.customer_id,)).fetchone():
            raise HTTPException(404, "Client introuvable")
        cur = con.execute(
            "INSERT INTO tickets(customer_id,subject,message,created_at) VALUES(?,?,?,?)",
            (t.customer_id, t.subject, t.message, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        return dict(con.execute("SELECT * FROM tickets WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/tickets")
def list_tickets(status: Optional[str] = None):
    q, args = "SELECT t.*, c.name AS customer_name FROM tickets t JOIN customers c ON c.id=t.customer_id", ()
    if status:
        q, args = q + " WHERE t.status=?", (status,)
    with db() as con:
        return [dict(r) for r in con.execute(q + " ORDER BY t.id DESC", args)]


@app.patch("/tickets/{tid}")
def patch_ticket(tid: int, p: TicketPatch):
    if p.status and p.status not in STATUSES:
        raise HTTPException(422, f"Statut invalide ({', '.join(sorted(STATUSES))})")
    with db() as con:
        if not con.execute("SELECT 1 FROM tickets WHERE id=?", (tid,)).fetchone():
            raise HTTPException(404, "Demande introuvable")
        for col, val in p.model_dump(exclude_none=True).items():
            con.execute(f"UPDATE tickets SET {col}=? WHERE id=?", (val, tid))
        return dict(con.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone())


# ---------- Assistant IA ----------
SYSTEM = (
    "Tu es un assistant de support client. Analyse le message du client et réponds UNIQUEMENT "
    'avec un JSON: {"topic": "facturation|technique|commercial|autre", '
    '"priority": "haute|normale|basse", "reply": "réponse polie en français, 3 phrases max"}.'
)
URGENT = ["urgent", "bloqué", "panne", "impossible", "immédiat", "erreur", "perdu", "rien ne marche"]
TOPICS = {"facturation": ["facture", "paiement", "prélèvement", "remboursement"],
          "technique": ["bug", "connexion", "mot de passe", "erreur", "panne", "accès"],
          "commercial": ["devis", "offre", "tarif", "contrat", "abonnement"]}


def heuristic(message: str) -> dict:
    """Plan B sans clé API : règles simples (la démo marche toujours)."""
    m = message.lower()
    topic = next((t for t, kws in TOPICS.items() if any(k in m for k in kws)), "autre")
    priority = "haute" if any(k in m for k in URGENT) else "normale"
    reply = ("Bonjour, merci pour votre message. Nous avons bien pris en compte votre demande "
             f"({topic}) et un conseiller vous répond dans les meilleurs délais.")
    return {"topic": topic, "priority": priority, "reply": reply, "source": "regles"}


def classify(message: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": os.getenv("AI_MODEL", "claude-haiku-5-5"), "max_tokens": 500,
                      "system": SYSTEM, "messages": [{"role": "user", "content": message}]},
                timeout=30)
            r.raise_for_status()
            data = json.loads(r.json()["content"][0]["text"])
            if data["priority"] in {"haute", "normale", "basse"} and data.get("reply"):
                return {"topic": data.get("topic", "autre"), "priority": data["priority"],
                        "reply": data["reply"], "source": "ia"}
        except Exception:
            pass  # on retombe sur les règles : l'app ne plante jamais à cause de l'IA
    return heuristic(message)


@app.post("/tickets/{tid}/analyze")
def analyze_ticket(tid: int):
    with db() as con:
        row = con.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
        if not row:
            raise HTTPException(404, "Demande introuvable")
        res = classify(row["message"])
        con.execute("UPDATE tickets SET priority=?, topic=?, ai_reply=? WHERE id=?",
                    (res["priority"], res["topic"], res["reply"], tid))
    return res


# ---------- Tableau de bord ----------
@app.get("/stats")
def stats():
    with db() as con:
        one = lambda q: con.execute(q).fetchone()[0]
        return {
            "total": one("SELECT COUNT(*) FROM tickets"),
            "nouvelles": one("SELECT COUNT(*) FROM tickets WHERE status='nouvelle'"),
            "en_cours": one("SELECT COUNT(*) FROM tickets WHERE status='en_cours'"),
            "resolues": one("SELECT COUNT(*) FROM tickets WHERE status='resolue'"),
            "urgentes_a_traiter": one("SELECT COUNT(*) FROM tickets WHERE priority='haute' AND status!='resolue'"),
            "clients": one("SELECT COUNT(*) FROM customers"),
        }
