from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import json, os, requests as req_lib

app = Flask(__name__)
app.secret_key = "slms-secret-key-2026"

# ─── IN-MEMORY DATABASE ───────────────────────────────────
BOOKS = [
    {"id": 1, "title": "Introduction to Python", "author": "John Smith", "category": "Technology", "price": 450, "copies": 5, "status": "active"},
    {"id": 2, "title": "Data Structures 101", "author": "Maria Santos", "category": "Technology", "price": 380, "copies": 3, "status": "active"},
    {"id": 3, "title": "Philippine History", "author": "Jose Reyes", "category": "History", "price": 300, "copies": 4, "status": "active"},
    {"id": 4, "title": "Calculus Made Easy", "author": "Ana Cruz", "category": "Math", "price": 500, "copies": 2, "status": "active"},
    {"id": 5, "title": "World Literature", "author": "Elena Bautista", "category": "Literature", "price": 350, "copies": 6, "status": "active"},
    {"id": 6, "title": "Biology Fundamentals", "author": "Marco Dela Cruz", "category": "Science", "price": 420, "copies": 3, "status": "active"},
    {"id": 7, "title": "Introduction to Economics", "author": "Lita Gomez", "category": "Social", "price": 390, "copies": 2, "status": "active"},
]

USERS = [
    {"id": 1, "username": "admin",    "email": "admin@library.com",   "password": "admin123",   "role": "librarian"},
    {"id": 2, "username": "staff1",   "email": "staff@library.com",   "password": "staff123",   "role": "staff"},
    {"id": 3, "username": "student1", "email": "student@library.com", "password": "student123", "role": "student"},
    {"id": 4, "username": "teacher1", "email": "teacher@library.com", "password": "teacher123", "role": "teacher"},
]

BORROWS = [
    {"id": 1, "userId": 3, "bookId": 1, "status": "borrowed", "borrowedAt": "2025-04-20", "dueDate": "2025-04-27", "returnedAt": None, "penalty": 0},
    {"id": 2, "userId": 4, "bookId": 3, "status": "returned", "borrowedAt": "2025-04-10", "dueDate": "2025-04-17", "returnedAt": "2025-04-15", "penalty": 0},
    {"id": 3, "userId": 3, "bookId": 5, "status": "overdue",  "borrowedAt": "2025-04-01", "dueDate": "2025-04-08", "returnedAt": None, "penalty": 70},
    {"id": 4, "userId": 4, "bookId": 2, "status": "borrowed", "borrowedAt": "2025-04-25", "dueDate": "2025-05-02", "returnedAt": None, "penalty": 0},
]

REQUESTS = [
    {"id": 1, "studentId": 3, "bookId": 4, "status": "pending",  "requestDate": "2025-04-30"},
    {"id": 2, "studentId": 3, "bookId": 6, "status": "approved", "requestDate": "2025-04-22"},
]

RESERVATIONS = [
    {"id": 1, "userId": 3, "bookId": 7, "status": "pending", "reservedAt": "2025-04-28"},
]

CATEGORY_COLORS = {
    "Technology": "#185FA5", "History": "#0F6E56", "Math": "#854F0B",
    "Literature": "#993C1D", "Science": "#3B6D11", "Social": "#993556", "Other": "#534AB7",
}

# ─── HELPERS ──────────────────────────────────────────────
def get_book(book_id):
    return next((b for b in BOOKS if b["id"] == book_id), None)

def get_user(user_id):
    return next((u for u in USERS if u["id"] == user_id), None)

def next_id(lst):
    return max((x["id"] for x in lst), default=0) + 1

def current_user():
    uid = session.get("user_id")
    return get_user(uid) if uid else None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ─────────────────────────────────────────────────
@app.route("/")
def index():
    if current_user():
        return redirect(url_for("app_page"))
    return redirect(url_for("login_page"))

@app.route("/login", methods=["GET"])
def login_page():
    if current_user():
        return redirect(url_for("app_page"))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    user = next((u for u in USERS if u["username"] == data.get("username") and u["password"] == data.get("password")), None)
    if user:
        session["user_id"] = user["id"]
        return jsonify({"ok": True, "user": {k: v for k, v in user.items() if k != "password"}})
    return jsonify({"ok": False, "error": "Invalid username or password."})

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    if not data.get("username") or not data.get("email") or not data.get("password"):
        return jsonify({"ok": False, "error": "All fields required."})
    if any(u["username"] == data["username"] for u in USERS):
        return jsonify({"ok": False, "error": "Username already taken."})
    new_user = {"id": next_id(USERS), "username": data["username"], "email": data["email"],
                "password": data["password"], "role": data.get("role", "student")}
    USERS.append(new_user)
    return jsonify({"ok": True})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/app")
@login_required
def app_page():
    user = current_user()
    return render_template("app.html", user=user,
                           category_colors=json.dumps(CATEGORY_COLORS))

# ─── BOOKS API ────────────────────────────────────────────
@app.route("/api/books", methods=["GET"])
@login_required
def api_books():
    return jsonify(BOOKS)

@app.route("/api/books", methods=["POST"])
@login_required
def api_add_book():
    data = request.json
    book = {"id": next_id(BOOKS), "title": data["title"], "author": data["author"],
            "category": data.get("category", "Other"), "price": float(data.get("price", 0)),
            "copies": int(data.get("copies", 1)), "status": "active"}
    BOOKS.append(book)
    return jsonify(book)

@app.route("/api/books/<int:book_id>", methods=["PUT"])
@login_required
def api_update_book(book_id):
    data = request.json
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Not found"}), 404
    book.update({"title": data["title"], "author": data["author"], "category": data["category"],
                 "price": float(data["price"]), "copies": int(data["copies"])})
    return jsonify(book)

@app.route("/api/books/<int:book_id>/archive", methods=["POST"])
@login_required
def api_archive_book(book_id):
    book = get_book(book_id)
    if not book:
        return jsonify({"error": "Not found"}), 404
    book["status"] = "active" if book["status"] == "archived" else "archived"
    return jsonify(book)

# ─── USERS API ────────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
@login_required
def api_users():
    safe = [{k: v for k, v in u.items() if k != "password"} for u in USERS]
    for u in safe:
        u["activeBorrows"] = sum(1 for b in BORROWS if b["userId"] == u["id"] and b["status"] == "borrowed")
    return jsonify(safe)

# ─── BORROWS API ──────────────────────────────────────────
@app.route("/api/borrows", methods=["GET"])
@login_required
def api_borrows():
    result = []
    for b in BORROWS:
        bk = get_book(b["bookId"])
        us = get_user(b["userId"])
        result.append({**b, "bookTitle": bk["title"] if bk else "Unknown", "username": us["username"] if us else "Unknown"})
    return jsonify(result)

@app.route("/api/borrows/<int:borrow_id>/return", methods=["POST"])
@login_required
def api_return_book(borrow_id):
    borrow = next((b for b in BORROWS if b["id"] == borrow_id), None)
    if not borrow:
        return jsonify({"error": "Not found"}), 404
    borrow["status"] = "returned"
    borrow["returnedAt"] = datetime.now().strftime("%Y-%m-%d")
    book = get_book(borrow["bookId"])
    if book:
        book["copies"] += 1
    return jsonify(borrow)

# ─── REQUESTS API ─────────────────────────────────────────
@app.route("/api/requests", methods=["GET"])
@login_required
def api_requests():
    result = []
    for r in REQUESTS:
        bk = get_book(r["bookId"])
        st = get_user(r["studentId"])
        result.append({**r, "bookTitle": bk["title"] if bk else "Unknown", "studentName": st["username"] if st else "Unknown"})
    return jsonify(result)

@app.route("/api/requests", methods=["POST"])
@login_required
def api_submit_request():
    data = request.json
    user = current_user()
    req = {"id": next_id(REQUESTS), "studentId": user["id"], "bookId": data["bookId"],
           "status": "pending", "requestDate": datetime.now().strftime("%Y-%m-%d")}
    REQUESTS.append(req)
    return jsonify(req)

@app.route("/api/requests/<int:req_id>/approve", methods=["POST"])
@login_required
def api_approve_request(req_id):
    req = next((r for r in REQUESTS if r["id"] == req_id), None)
    if not req:
        return jsonify({"error": "Not found"}), 404
    req["status"] = "approved"
    due = datetime.now() + timedelta(days=7)
    borrow = {"id": next_id(BORROWS), "userId": req["studentId"], "bookId": req["bookId"],
              "status": "borrowed", "borrowedAt": datetime.now().strftime("%Y-%m-%d"),
              "dueDate": due.strftime("%Y-%m-%d"), "returnedAt": None, "penalty": 0}
    BORROWS.append(borrow)
    book = get_book(req["bookId"])
    if book:
        book["copies"] = max(0, book["copies"] - 1)
    return jsonify(req)

@app.route("/api/requests/<int:req_id>/decline", methods=["POST"])
@login_required
def api_decline_request(req_id):
    req = next((r for r in REQUESTS if r["id"] == req_id), None)
    if not req:
        return jsonify({"error": "Not found"}), 404
    req["status"] = "declined"
    return jsonify(req)

# ─── RESERVATIONS API ─────────────────────────────────────
@app.route("/api/reservations", methods=["GET"])
@login_required
def api_reservations():
    result = []
    for r in RESERVATIONS:
        bk = get_book(r["bookId"])
        result.append({**r, "bookTitle": bk["title"] if bk else "Unknown"})
    return jsonify(result)

@app.route("/api/reservations", methods=["POST"])
@login_required
def api_add_reservation():
    data = request.json
    user = current_user()
    res = {"id": next_id(RESERVATIONS), "userId": user["id"], "bookId": data["bookId"],
           "status": "pending", "reservedAt": datetime.now().strftime("%Y-%m-%d")}
    RESERVATIONS.append(res)
    return jsonify(res)

# ─── ANALYTICS API ────────────────────────────────────────
@app.route("/api/analytics", methods=["GET"])
@login_required
def api_analytics():
    total_books = sum(1 for b in BOOKS if b["status"] != "archived")
    total_borrowed = sum(1 for b in BORROWS if b["status"] == "borrowed")
    total_overdue = sum(1 for b in BORROWS if b["status"] == "overdue")
    total_returned = sum(1 for b in BORROWS if b["status"] == "returned")
    total_penalties = sum(b.get("penalty", 0) for b in BORROWS)
    pending_reqs = sum(1 for r in REQUESTS if r["status"] == "pending")

    cat_map = {}
    for b in BORROWS:
        bk = get_book(b["bookId"])
        if bk:
            cat_map[bk["category"]] = cat_map.get(bk["category"], 0) + 1

    book_borrow = {}
    for b in BORROWS:
        book_borrow[b["bookId"]] = book_borrow.get(b["bookId"], 0) + 1
    top_books = sorted(book_borrow.items(), key=lambda x: x[1], reverse=True)[:5]
    top_books_data = [{"title": (get_book(int(bid)) or {}).get("title", "Unknown"), "count": cnt} for bid, cnt in top_books]

    weekly = [{"label": d, "value": v} for d, v in
              [("Mon",2),("Tue",5),("Wed",3),("Thu",7),("Fri",4),("Sat",1),("Sun",0)]]

    return jsonify({
        "totalBooks": total_books, "totalBorrowed": total_borrowed,
        "totalOverdue": total_overdue, "totalReturned": total_returned,
        "totalPenalties": total_penalties, "pendingRequests": pending_reqs,
        "categoryData": [{"cat": k, "count": v} for k, v in sorted(cat_map.items(), key=lambda x: x[1], reverse=True)],
        "topBooks": top_books_data, "weekly": weekly,
    })

# ─── CHATBOT API ──────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.json
    messages = data.get("messages", [])
    user = current_user()

    active_books = [b for b in BOOKS if b["status"] != "archived"]
    my_borrows = [b for b in BORROWS if b["userId"] == user["id"] and b["status"] == "borrowed"]
    my_reqs = [r for r in REQUESTS if r["studentId"] == user["id"] and r["status"] == "pending"]
    total_borrowed = sum(1 for b in BORROWS if b["status"] == "borrowed")
    overdue = sum(1 for b in BORROWS if b["status"] == "overdue")
    pending = sum(1 for r in REQUESTS if r["status"] == "pending")

    book_list = "\n".join(f'- "{b["title"]}" by {b["author"]} ({b["category"]}) — ₱{b["price"]}, {b["copies"]} copies'
                          for b in active_books[:7])

    my_borrows_txt = "None"
    if my_borrows:
        my_borrows_txt = "\n".join(f'- "{(get_book(b["bookId"]) or {}).get("title","Unknown")}" due {b["dueDate"]}' for b in my_borrows)

    my_reqs_txt = "None"
    if my_reqs:
        my_reqs_txt = "\n".join(f'- "{(get_book(r["bookId"]) or {}).get("title","Unknown")}"' for r in my_reqs)

    system_prompt = f"""You are a helpful library assistant for a school Library Management System in the Philippines.
Current user: {user['username']} ({user['role']})
Today: {datetime.now().strftime('%B %d, %Y')}

Library stats:
- Total active books: {len(active_books)}
- Currently borrowed system-wide: {total_borrowed}
- Overdue books: {overdue}
- Pending borrow requests: {pending}

Available books (sample):
{book_list}

User's current borrows:
{my_borrows_txt}

User's pending requests:
{my_reqs_txt}

Respond helpfully, concisely, and in a friendly tone. If asked about specific data you don't have, acknowledge the limitation. Keep responses under 150 words unless detail is needed."""

    try:
        response = req_lib.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": messages[-10:],
            },
            timeout=30
        )
        result = response.json()
        reply = result.get("content", [{}])[0].get("text", "Sorry, I couldn't process that.")
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"ok": False, "reply": "Sorry, I'm having trouble connecting right now."})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
