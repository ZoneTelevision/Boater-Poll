"""Boater Poll: Crusader vs MerCruiser.

Run:  pip install flask  &&  python app.py   -> prints the address (first free port from 8420)
Admin CSV export: /export.csv?key=<POLL_ADMIN_KEY>
"""
import csv
import hashlib
import io
import json
import os
import secrets
import sqlite3
from collections import Counter
from datetime import datetime, timezone

from flask import (Flask, Response, abort, g, make_response, redirect,
                   render_template, request, url_for)

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("POLL_DB", os.path.join(BASE, "poll.db"))
ADMIN_KEY = os.environ.get("POLL_ADMIN_KEY", "change-me")

app = Flask(__name__)
app.secret_key = os.environ.get("POLL_SECRET", secrets.token_hex(16))

BRANDS = {"crusader": "Crusader", "mercruiser": "MerCruiser"}
REASONS = [
    "Reliability", "Parts availability", "Dealer / service network",
    "Power & torque", "Fuel economy", "Purchase price",
    "Build quality / marinization", "Cooling system",
    "Ease of DIY maintenance", "Past experience", "Resale value", "Looks",
]
BOAT_TYPES = ["Inboard", "V-drive", "Sterndrive (I/O)", "Not sure / no boat"]
WATERS = ["Fresh", "Salt", "Both / brackish"]
OWNED = ["Crusader", "MerCruiser", "Both", "Neither"]
EXPERIENCE = ["Under 5 years", "5–15 years", "15–30 years", "30+ years"]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            voter TEXT NOT NULL UNIQUE,
            choice TEXT NOT NULL,
            reasons TEXT NOT NULL,
            why TEXT,
            boat_type TEXT, water TEXT, owned TEXT, experience TEXT,
            region TEXT, name TEXT
        )""")


def voter_id():
    """One vote per browser (cookie), with an IP hash fallback."""
    token = request.cookies.get("poll_voter")
    if token:
        return token, False
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    return hashlib.sha256((ip.split(",")[0].strip() + secrets.token_hex(8)).encode()).hexdigest()[:32], True


def pick(value, allowed):
    return value if value in allowed else None


def tally():
    rows = db().execute("SELECT * FROM votes ORDER BY id DESC").fetchall()
    totals = Counter(r["choice"] for r in rows)
    reasons = {b: Counter() for b in BRANDS}
    owned_vs = Counter()
    for r in rows:
        for reason in json.loads(r["reasons"]):
            reasons[r["choice"]][reason] += 1
        if r["owned"]:
            owned_vs[(r["owned"], r["choice"])] += 1
    comments = [r for r in rows if r["why"]][:30]
    return rows, totals, reasons, owned_vs, comments


@app.route("/")
def poll():
    token = request.cookies.get("poll_voter")
    existing = None
    if token:
        existing = db().execute("SELECT * FROM votes WHERE voter=?", (token,)).fetchone()
    total = db().execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    return render_template(
        "poll.html", reasons=REASONS, boat_types=BOAT_TYPES, waters=WATERS,
        owned=OWNED, experience=EXPERIENCE, existing=existing, total=total,
        existing_reasons=json.loads(existing["reasons"]) if existing else [],
        error=request.args.get("error"))


@app.route("/vote", methods=["POST"])
def vote():
    f = request.form
    choice = f.get("choice")
    if choice not in BRANDS:
        return redirect(url_for("poll", error="Pick Crusader or MerCruiser."))
    reasons = [r for r in f.getlist("reasons") if r in REASONS]
    if not reasons:
        return redirect(url_for("poll", error="Pick at least one reason."))
    why = (f.get("why") or "").strip()[:1000] or None
    voter, is_new = voter_id()
    data = (
        datetime.now(timezone.utc).isoformat(timespec="seconds"), voter, choice,
        json.dumps(reasons), why, pick(f.get("boat_type"), BOAT_TYPES),
        pick(f.get("water"), WATERS), pick(f.get("owned"), OWNED),
        pick(f.get("experience"), EXPERIENCE),
        (f.get("region") or "").strip()[:60] or None,
        (f.get("name") or "").strip()[:40] or None,
    )
    db().execute("""INSERT INTO votes (created_at, voter, choice, reasons, why, boat_type,
        water, owned, experience, region, name) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(voter) DO UPDATE SET created_at=excluded.created_at,
        choice=excluded.choice, reasons=excluded.reasons, why=excluded.why,
        boat_type=excluded.boat_type, water=excluded.water, owned=excluded.owned,
        experience=excluded.experience, region=excluded.region, name=excluded.name""", data)
    db().commit()
    resp = make_response(redirect(url_for("results", voted=1)))
    if is_new:
        resp.set_cookie("poll_voter", voter, max_age=60 * 60 * 24 * 365 * 2,
                        httponly=True, samesite="Lax")
    return resp


@app.route("/results")
def results():
    rows, totals, reasons, owned_vs, comments = tally()
    n = len(rows)
    pct = {b: round(100 * totals[b] / n) if n else 0 for b in BRANDS}
    top = {b: reasons[b].most_common(6) for b in BRANDS}
    return render_template(
        "results.html", n=n, totals=totals, pct=pct, top=top, brands=BRANDS,
        owned_vs=owned_vs, owned=OWNED, comments=comments,
        voted=request.args.get("voted"))


@app.route("/export.csv")
def export():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)
    rows = db().execute("SELECT * FROM votes ORDER BY id").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["id", "created_at", "choice", "reasons", "why", "boat_type", "water",
            "owned", "experience", "region", "name"]
    w.writerow(cols)
    for r in rows:
        w.writerow([", ".join(json.loads(r[c])) if c == "reasons" else r[c] for c in cols])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=boater_poll.csv"})


init_db()

def free_port(start=8420, tries=50):
    """First port from `start` that nothing else (AirPlay, other apps) is using."""
    import socket
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise SystemExit("No free port found; set one with PORT=xxxx python3 app.py")


if __name__ == "__main__":
    port = int(os.environ["PORT"]) if os.environ.get("PORT") else free_port()
    print(f"\n  Boater Poll is running ->  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
