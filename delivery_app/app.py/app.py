
import os
import math
import sqlite3
import random
import hmac
from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, send_from_directory)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "HASIFAHAMED2007")

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.db")
STATUSES = ["New", "Picked up", "Delivered", "Cancelled"]


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT,
                pickup TEXT,
                drop_loc TEXT,
                item TEXT,
                km REAL,
                fee INTEGER,
                status TEXT DEFAULT 'New',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def calc_fee(km):
    if km <= 2:
        return 30
    if km <= 5:
        return 50
    if km <= 8:
        return 80
    return 80 + math.ceil(km - 8) * 10


def is_admin():
    return session.get("admin") is True

@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(app.static_folder, "sw.js")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/order", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    pickup = (data.get("pickup") or "").strip()
    drop = (data.get("drop") or "").strip()
    item = (data.get("item") or "").strip()
    name = (data.get("name") or "").strip()

    try:
        km = float(data.get("km"))
    except (TypeError, ValueError):
        km = 0

    if not pickup or not drop or not item or km <= 0:
        return jsonify(error="Please fill pickup, drop, item and distance."), 400

    fee = calc_fee(km)

    with get_db() as db:
        for _ in range(20):
            code = "NOE" + str(random.randint(1000, 9999))
            try:
                db.execute(
                    "INSERT INTO orders (code, name, pickup, drop_loc, item, km, fee) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (code, name, pickup, drop, item, km, fee),
                )
                return jsonify(code=code, fee=fee)
            except sqlite3.IntegrityError:
                continue

    return jsonify(error="Could not save the order. Try again."), 500


# ---------- Admin ----------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""
    if request.method == "POST":
        pw = request.form.get("password", "")
        if hmac.compare_digest(pw.encode(), ADMIN_PASSWORD.encode()):
            session["admin"] = True
            return redirect(url_for("admin"))
        error = "Wrong password."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin():
    if not is_admin():
        return redirect(url_for("admin_login"))

    selected = request.args.get("status", "")
    with get_db() as db:
        if selected in STATUSES:
            orders = db.execute(
                "SELECT * FROM orders WHERE status=? ORDER BY id DESC", (selected,)
            ).fetchall()
        else:
            orders = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()

        counts = {s: 0 for s in STATUSES}
        for row in db.execute("SELECT status, COUNT(*) c FROM orders GROUP BY status"):
            counts[row["status"]] = row["c"]

        earned = db.execute(
            "SELECT COALESCE(SUM(fee),0) FROM orders WHERE status='Delivered'"
        ).fetchone()[0]

    return render_template("admin.html", orders=orders, statuses=STATUSES,
                           counts=counts, selected=selected, earned=earned)


@app.route("/admin/status/<int:order_id>", methods=["POST"])
def admin_status(order_id):
    if not is_admin():
        return redirect(url_for("admin_login"))
    status = request.form.get("status")
    if status in STATUSES:
        with get_db() as db:
            db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    return redirect(request.referrer or url_for("admin"))

@app.route("/track")
def track():
    code = request.args.get("code", "").strip().upper()
    order = None
    if code:
        with get_db() as db:
            order = db.execute(
                "SELECT code, status, created_at, fee FROM orders WHERE code=?",
                (code,),
            ).fetchone()
    return render_template("track.html", code=code, order=order,
                           steps=["New", "Picked up", "Delivered"])


init_db()

if __name__ == "__main__":
    app.run(debug=True)