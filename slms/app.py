from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import json, requests as req_lib
import mysql.connector

app = Flask(__name__)
app.secret_key = "slms-secret-key-2026"

# ─── DATABASE CONFIG ──────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "09192004",        # blank ang default password sa XAMPP
    "database": "library_db"
}

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

def init_db():
    conn = mysql.connector.connect(host=DB_CONFIG["host"],
                                   user=DB_CONFIG["user"],
                                   password=DB_CONFIG["password"])
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS library_db")
    cursor.execute("USE library_db")

    # Avoid failing on duplicate seed data during reload/restart
    cursor.execute("SET SQL_SAFE_UPDATES = 0")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(150) NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'student',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            price DECIMAL(10,2) DEFAULT 0,
            copies INT DEFAULT 1,
            status VARCHAR(50) DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrows (
            id INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            bookId INT NOT NULL,
            status VARCHAR(50) DEFAULT 'borrowed',
            borrowedAt DATE,
            dueDate DATE,
            returnedAt DATE,
            penalty DECIMAL(10,2) DEFAULT 0,
            FOREIGN KEY (userId) REFERENCES users(id),
            FOREIGN KEY (bookId) REFERENCES books(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrow_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            studentId INT NOT NULL,
            bookId INT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            requestDate DATE,
            FOREIGN KEY (studentId) REFERENCES users(id),
            FOREIGN KEY (bookId) REFERENCES books(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            userId INT NOT NULL,
            bookId INT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            reservedAt DATE,
            FOREIGN KEY (userId) REFERENCES users(id),
            FOREIGN KEY (bookId) REFERENCES books(id)
        )
    """)

    # Seed default users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)
        """, [
            ("admin",    "admin@library.com",   "admin123",   "librarian"),
            ("staff1",   "staff@library.com",   "staff123",   "staff"),
            ("student1", "student@library.com", "student123", "student"),
            ("teacher1", "teacher@library.com", "teacher123", "teacher"),
        ])

    # Seed default books
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO books (title, author, category, price, copies) VALUES (%s, %s, %s, %s, %s)
        """, [
            ("Introduction to Python",    "John Smith",      "Technology", 450, 5),
            ("Data Structures 101",       "Maria Santos",    "Technology", 380, 3),
            ("Philippine History",        "Jose Reyes",      "History",    300, 4),
            ("Calculus Made Easy",        "Ana Cruz",        "Math",       500, 2),
            ("World Literature",          "Elena Bautista",  "Literature", 350, 6),
            ("Biology Fundamentals",      "Marco Dela Cruz", "Science",    420, 3),
            ("Introduction to Economics", "Lita Gomez",      "Social",     390, 2),
        ])

    conn.commit()
    cursor.close()
    conn.close()
    print(" Database initialized!")

CATEGORY_COLORS = {
    "Technology": "#185FA5", "History": "#0F6E56", "Math": "#854F0B",
    "Literature": "#993C1D", "Science": "#3B6D11", "Social": "#993556", "Other": "#534AB7",
}

# ─── HELPERS ──────────────────────────────────────────────
def query(sql, params=(), one=False, commit=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    if commit:
        conn.commit()
        result = cursor.lastrowid
    elif one:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return query("SELECT * FROM users WHERE id = %s", (uid,), one=True)

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
    user = query("SELECT * FROM users WHERE username=%s AND password=%s",
                 (data.get("username"), data.get("password")), one=True)
    if user:
        session["user_id"] = user["id"]
        safe = {k: v for k, v in user.items() if k != "password"}
        return jsonify({"ok": True, "user": safe})
    return jsonify({"ok": False, "error": "Invalid username or password."})

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json
    if not data.get("username") or not data.get("email") or not data.get("password"):
        return jsonify({"ok": False, "error": "All fields required."})
    existing = query("SELECT id FROM users WHERE username=%s", (data["username"],), one=True)
    if existing:
        return jsonify({"ok": False, "error": "Username already taken."})
    query("INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
          (data["username"], data["email"], data["password"], data.get("role", "student")), commit=True)
    return jsonify({"ok": True})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/app")
@login_required
def app_page():
    user = current_user()
    return render_template("app.html", user=user, category_colors=json.dumps(CATEGORY_COLORS))

# ─── BOOKS API ────────────────────────────────────────────
@app.route("/api/books", methods=["GET"])
@login_required
def api_books():
    books = query("SELECT * FROM books")
    return jsonify(books)

@app.route("/api/books", methods=["POST"])
@login_required
def api_add_book():
    data = request.json
    new_id = query(
        "INSERT INTO books (title, author, category, price, copies) VALUES (%s,%s,%s,%s,%s)",
        (data["title"], data["author"], data.get("category","Other"),
         float(data.get("price",0)), int(data.get("copies",1))), commit=True)
    book = query("SELECT * FROM books WHERE id=%s", (new_id,), one=True)
    return jsonify(book)

@app.route("/api/books/<int:book_id>", methods=["PUT"])
@login_required
def api_update_book(book_id):
    data = request.json
    query("UPDATE books SET title=%s, author=%s, category=%s, price=%s, copies=%s WHERE id=%s",
          (data["title"], data["author"], data["category"],
           float(data["price"]), int(data["copies"]), book_id), commit=True)
    book = query("SELECT * FROM books WHERE id=%s", (book_id,), one=True)
    return jsonify(book)

@app.route("/api/books/<int:book_id>/archive", methods=["POST"])
@login_required
def api_archive_book(book_id):
    book = query("SELECT * FROM books WHERE id=%s", (book_id,), one=True)
    if not book:
        return jsonify({"error": "Not found"}), 404
    new_status = "active" if book["status"] == "archived" else "archived"
    query("UPDATE books SET status=%s WHERE id=%s", (new_status, book_id), commit=True)
    book["status"] = new_status
    return jsonify(book)

# ─── USERS API ────────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
@login_required
def api_users():
    users = query("SELECT id, username, email, role, created_at FROM users")
    for u in users:
        u["activeBorrows"] = query(
            "SELECT COUNT(*) as cnt FROM borrows WHERE userId=%s AND status='borrowed'",
            (u["id"],), one=True)["cnt"]
    return jsonify(users)

# ─── BORROWS API ──────────────────────────────────────────
@app.route("/api/borrows", methods=["GET"])
@login_required
def api_borrows():
    rows = query("""
        SELECT b.*, u.username, bk.title AS bookTitle
        FROM borrows b
        JOIN users u ON u.id = b.userId
        JOIN books bk ON bk.id = b.bookId
        ORDER BY b.borrowedAt DESC
    """)
    return jsonify(rows)

@app.route("/api/borrows/<int:borrow_id>/return", methods=["POST"])
@login_required
def api_return_book(borrow_id):
    today = datetime.now().strftime("%Y-%m-%d")
    borrow = query("SELECT * FROM borrows WHERE id=%s", (borrow_id,), one=True)
    if not borrow:
        return jsonify({"error": "Not found"}), 404
    query("UPDATE borrows SET status='returned', returnedAt=%s WHERE id=%s",
          (today, borrow_id), commit=True)
    query("UPDATE books SET copies = copies + 1 WHERE id=%s", (borrow["bookId"],), commit=True)
    return jsonify({"ok": True})

# ─── REQUESTS API ─────────────────────────────────────────
@app.route("/api/requests", methods=["GET"])
@login_required
def api_requests():
    rows = query("""
        SELECT br.*, u.username AS studentName, bk.title AS bookTitle
        FROM borrow_requests br
        JOIN users u ON u.id = br.studentId
        JOIN books bk ON bk.id = br.bookId
        ORDER BY br.requestDate DESC
    """)
    return jsonify(rows)

@app.route("/api/requests", methods=["POST"])
@login_required
def api_submit_request():
    data = request.json
    user = current_user()
    today = datetime.now().strftime("%Y-%m-%d")
    new_id = query(
        "INSERT INTO borrow_requests (studentId, bookId, status, requestDate) VALUES (%s,%s,'pending',%s)",
        (user["id"], data["bookId"], today), commit=True)
    req = query("SELECT * FROM borrow_requests WHERE id=%s", (new_id,), one=True)
    return jsonify(req)

@app.route("/api/requests/<int:req_id>/approve", methods=["POST"])
@login_required
def api_approve_request(req_id):
    req = query("SELECT * FROM borrow_requests WHERE id=%s", (req_id,), one=True)
    if not req:
        return jsonify({"error": "Not found"}), 404
    today = datetime.now().strftime("%Y-%m-%d")
    due = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    query("UPDATE borrow_requests SET status='approved' WHERE id=%s", (req_id,), commit=True)
    query("""INSERT INTO borrows (userId, bookId, status, borrowedAt, dueDate, penalty)
             VALUES (%s,%s,'borrowed',%s,%s,0)""",
          (req["studentId"], req["bookId"], today, due), commit=True)
    query("UPDATE books SET copies = GREATEST(0, copies - 1) WHERE id=%s", (req["bookId"],), commit=True)
    return jsonify({"ok": True})

@app.route("/api/requests/<int:req_id>/decline", methods=["POST"])
@login_required
def api_decline_request(req_id):
    query("UPDATE borrow_requests SET status='declined' WHERE id=%s", (req_id,), commit=True)
    return jsonify({"ok": True})

# ─── RESERVATIONS API ─────────────────────────────────────
@app.route("/api/reservations", methods=["GET"])
@login_required
def api_reservations():
    rows = query("""
        SELECT r.*, bk.title AS bookTitle, u.username
        FROM reservations r
        JOIN books bk ON bk.id = r.bookId
        JOIN users u ON u.id = r.userId
        ORDER BY r.reservedAt DESC
    """)
    return jsonify(rows)

@app.route("/api/reservations", methods=["POST"])
@login_required
def api_add_reservation():
    data = request.json
    user = current_user()
    today = datetime.now().strftime("%Y-%m-%d")
    new_id = query(
        "INSERT INTO reservations (userId, bookId, status, reservedAt) VALUES (%s,%s,'pending',%s)",
        (user["id"], data["bookId"], today), commit=True)
    res = query("SELECT * FROM reservations WHERE id=%s", (new_id,), one=True)
    return jsonify(res)

# ─── ANALYTICS API ────────────────────────────────────────
@app.route("/api/analytics", methods=["GET"])
@login_required
def api_analytics():
    total_books   = query("SELECT COUNT(*) as c FROM books WHERE status != 'archived'", one=True)["c"]
    total_borrowed= query("SELECT COUNT(*) as c FROM borrows WHERE status='borrowed'", one=True)["c"]
    total_overdue = query("SELECT COUNT(*) as c FROM borrows WHERE status='overdue'", one=True)["c"]
    total_returned= query("SELECT COUNT(*) as c FROM borrows WHERE status='returned'", one=True)["c"]
    total_penalties=query("SELECT COALESCE(SUM(penalty),0) as s FROM borrows", one=True)["s"]
    pending_reqs  = query("SELECT COUNT(*) as c FROM borrow_requests WHERE status='pending'", one=True)["c"]

    cat_data = query("""
        SELECT bk.category AS cat, COUNT(*) AS count
        FROM borrows br JOIN books bk ON bk.id = br.bookId
        GROUP BY bk.category ORDER BY count DESC
    """)

    top_books = query("""
        SELECT bk.title, COUNT(*) AS count
        FROM borrows br JOIN books bk ON bk.id = br.bookId
        GROUP BY br.bookId ORDER BY count DESC LIMIT 5
    """)

    weekly = [{"label": d, "value": v} for d, v in
              [("Mon",2),("Tue",5),("Wed",3),("Thu",7),("Fri",4),("Sat",1),("Sun",0)]]

    return jsonify({
        "totalBooks": total_books, "totalBorrowed": total_borrowed,
        "totalOverdue": total_overdue, "totalReturned": total_returned,
        "totalPenalties": float(total_penalties), "pendingRequests": pending_reqs,
        "categoryData": cat_data, "topBooks": top_books, "weekly": weekly,
    })

# ─── CHATBOT API ──────────────────────────────────────────
import time
import traceback

GEMINI_API_KEY = "AIzaSyCwPejSnALmYI9rDsXjXCo5uMUIQYfZqmA"

@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.json
    messages = data.get("messages", [])
    user = current_user()

    # 1. Fetch Dynamic Context from Database
    active_books   = query("SELECT * FROM books WHERE status != 'archived' LIMIT 7")
    my_borrows     = query("SELECT br.*, bk.title FROM borrows br JOIN books bk ON bk.id=br.bookId WHERE br.userId=%s AND br.status='borrowed'", (user["id"],))
    my_reqs        = query("SELECT rq.*, bk.title FROM borrow_requests rq JOIN books bk ON bk.id=rq.bookId WHERE rq.studentId=%s AND rq.status='pending'", (user["id"],))
    total_borrowed = query("SELECT COUNT(*) as c FROM borrows WHERE status='borrowed'", one=True)["c"]
    overdue        = query("SELECT COUNT(*) as c FROM borrows WHERE status='overdue'", one=True)["c"]
    pending        = query("SELECT COUNT(*) as c FROM borrow_requests WHERE status='pending'", one=True)["c"]

    book_list = "\n".join(f'- "{b["title"]}" by {b["author"]} ({b["category"]}) — {b["copies"]} copies available' for b in active_books)
    my_borrows_txt = "\n".join(f'- "{b["title"]}" (Due: {b["dueDate"]})' for b in my_borrows) or "No active borrows."
    my_reqs_txt    = "\n".join(f'- "{r["title"]}"' for r in my_reqs) or "No pending requests."

    system_prompt = f"""You are a helpful school library assistant in the Philippines.
User: {user['username']} ({user['role']}) | Date: {datetime.now().strftime('%B %d, %Y')}

Library Status:
- Books available: {len(active_books)}
- System-wide borrows: {total_borrowed}
- Overdue: {overdue}
- Pending requests: {pending}

Books you can recommend:
{book_list}

User's current status:
- Borrows: {my_borrows_txt}
- Requests: {my_reqs_txt}

Guidelines: Be friendly, concise (under 150 words), and prioritize helping the user with their borrows or finding books."""

    # 2. Format Conversation History (Fixing Gemini's alternating role requirement)
    raw = messages[-10:]
    gemini_messages = []
    last_role = None

    for m in raw:
        role = "user" if m["role"] == "user" else "model"
        if role == last_role:
            gemini_messages[-1]["parts"][0]["text"] += "\n" + m["content"]
        else:
            gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})
            last_role = role

    if not gemini_messages or gemini_messages[0]["role"] != "user":
        gemini_messages.insert(0, {"role": "user", "parts": [{"text": "Hello, I need help with the library."}]})

    # 3. Robust API Call with Failover & Retries
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro"]
    max_retries = 2

    for attempt in range(max_retries + 1):
        for model in models_to_try:
            try:
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"
                response = req_lib.post(
                    api_url,
                    params={"key": GEMINI_API_KEY},
                    headers={"Content-Type": "application/json"},
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": gemini_messages,
                        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.7}
                    },
                    timeout=25
                )
                
                result = response.json()

                if "candidates" in result:
                    reply = result["candidates"][0]["content"]["parts"][0]["text"]
                    return jsonify({"ok": True, "reply": reply})
                
                # Handle Overload/Rate Limit: Try next model or wait
                error_code = result.get("error", {}).get("code")
                error_msg = result.get("error", {}).get("message", "").lower()
                
                if error_code in [429, 503] or "high demand" in error_msg:
                    print(f"⚠️ Model {model} busy. Attempting failover...")
                    continue 

                return jsonify({"ok": False, "reply": f"API Error: {error_msg}"})

            except Exception as e:
                print(f" Connection error with {model}: {str(e)}")
                continue

        # Wait longer between major retries (Exponential Backoff)
        time.sleep(2 * (attempt + 1))

    return jsonify({"ok": False, "reply": "I'm currently receiving too many requests. Please try again in a few seconds!"})

# ─── MAIN ─────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)