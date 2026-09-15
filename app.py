from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__, static_folder="Static1")

DATABASE = "lost_found.db"


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# CREATE DATABASE
# -----------------------------
def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            color TEXT,
            location TEXT NOT NULL,
            date TEXT,
            description TEXT,
            contact TEXT,
            claimed INTEGER DEFAULT 0,
            status TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# ADD NEW COLUMNS TO OLD DATABASE
# -----------------------------
def add_contact_column():
    conn = get_db()

    # Add contact column if it does not already exist
    try:
        conn.execute(
            "ALTER TABLE items ADD COLUMN contact TEXT"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Add claimed column if it does not already exist
    try:
        conn.execute(
            "ALTER TABLE items ADD COLUMN claimed INTEGER DEFAULT 0"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.close()


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# REPORT LOST ITEM
# -----------------------------
@app.route("/lost", methods=["POST"])
def lost_item():

    item_name = request.form["item_name"]
    category = request.form["category"]
    color = request.form["color"]
    location = request.form["location"]
    date = request.form["date"]
    description = request.form["description"]
    contact = request.form.get("contact", "")

    conn = get_db()

    conn.execute("""
        INSERT INTO items
        (
            item_name,
            category,
            color,
            location,
            date,
            description,
            contact,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_name,
        category,
        color,
        location,
        date,
        description,
        contact,
        "Lost"
    ))

    conn.commit()
    conn.close()

    return "Lost item saved successfully!"


# -----------------------------
# REPORT FOUND ITEM
# -----------------------------
@app.route("/found", methods=["POST"])
def found_item():

    item_name = request.form["item_name"]
    category = request.form["category"]
    color = request.form["color"]
    location = request.form["location"]
    date = request.form["date"]
    description = request.form["description"]
    contact = request.form.get("contact", "")

    conn = get_db()

    conn.execute("""
        INSERT INTO items
        (
            item_name,
            category,
            color,
            location,
            date,
            description,
            contact,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_name,
        category,
        color,
        location,
        date,
        description,
        contact,
        "Found"
    ))

    conn.commit()
    conn.close()

    return "Found item saved successfully!"


# -----------------------------
# VIEW ALL ITEMS + SEARCH
# -----------------------------
@app.route("/items")
def items():

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    conn = get_db()

    query = "SELECT * FROM items WHERE 1=1"
    values = []

    # Search
    if search:

        query += """
            AND (
                item_name LIKE ?
                OR category LIKE ?
                OR color LIKE ?
                OR location LIKE ?
            )
        """

        search_value = "%" + search + "%"

        values.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    # Filter by Lost / Found
    if status:

        query += " AND status = ?"

        values.append(status)

    # Latest items first
    query += " ORDER BY id DESC"

    items = conn.execute(
        query,
        values
    ).fetchall()

    conn.close()

    return render_template(
        "items.html",
        items=items
    )


# -----------------------------
# SMART MATCHING
# -----------------------------
@app.route("/matches")
def matches():

    conn = get_db()

    lost_items = conn.execute(
        "SELECT * FROM items WHERE status = 'Lost'"
    ).fetchall()

    found_items = conn.execute(
        "SELECT * FROM items WHERE status = 'Found'"
    ).fetchall()

    matches = []

    # Compare every lost item with every found item
    for lost in lost_items:

        for found in found_items:

            score = 0

            lost_name = lost["item_name"].lower().strip()
            found_name = found["item_name"].lower().strip()

            lost_category = lost["category"].lower().strip()
            found_category = found["category"].lower().strip()

            lost_color = (lost["color"] or "").lower().strip()
            found_color = (found["color"] or "").lower().strip()

            lost_location = lost["location"].lower().strip()
            found_location = found["location"].lower().strip()

            # Item name = 40 points
            if lost_name == found_name:
                score += 40

            # Category = 20 points
            if lost_category == found_category:
                score += 20

            # Color = 20 points
            if lost_color == found_color:
                score += 20

            # Location = 20 points
            if lost_location == found_location:
                score += 20

            # Match threshold = 60
            if score >= 60:
                matches.append(
                    (lost, found, score)
                )

    conn.close()

    return render_template(
        "matches.html",
        matches=matches
    )


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():

    conn = get_db()

    # Count lost items
    lost_count = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status = 'Lost'"
    ).fetchone()[0]

    # Count found items
    found_count = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status = 'Found'"
    ).fetchone()[0]

    # Get lost and found items
    lost_items = conn.execute(
        "SELECT * FROM items WHERE status = 'Lost'"
    ).fetchall()

    found_items = conn.execute(
        "SELECT * FROM items WHERE status = 'Found'"
    ).fetchall()

    # Calculate match count
    match_count = 0

    for lost in lost_items:

        for found in found_items:

            score = 0

            if lost["item_name"].lower().strip() == found["item_name"].lower().strip():
                score += 40

            if lost["category"].lower().strip() == found["category"].lower().strip():
                score += 20

            if (lost["color"] or "").lower().strip() == (found["color"] or "").lower().strip():
                score += 20

            if lost["location"].lower().strip() == found["location"].lower().strip():
                score += 20

            if score >= 60:
                match_count += 1

    conn.close()

    return render_template(
        "dashboard.html",
        lost_count=lost_count,
        found_count=found_count,
        match_count=match_count
    )


# -----------------------------
# CLAIM ITEM
# -----------------------------
@app.route("/claim/<int:item_id>", methods=["POST"])
def claim_item(item_id):

    conn = get_db()

    conn.execute(
        "UPDATE items SET claimed = 1 WHERE id = ?",
        (item_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("items"))


# -----------------------------
# START APPLICATION
# -----------------------------
if __name__ == "__main__":

    create_database()

    add_contact_column()

    app.run(debug=True)
