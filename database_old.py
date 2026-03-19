import sqlite3

DB_FILE = "fleet.db"

# -----------------------------
# Initialize DB — run on startup
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fleet owners table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fleet_owners (
            owner_id        TEXT PRIMARY KEY,
            line_user_id    TEXT NOT NULL,
            name            TEXT,
            phone           TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Location history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    TEXT NOT NULL,
            vehicle_id  TEXT NOT NULL,
            driver_name TEXT,
            latitude    REAL NOT NULL,
            longitude   REAL NOT NULL,
            speed       REAL DEFAULT 0,
            status      TEXT DEFAULT 'unknown',
            sent_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed dummy owners for POC
    seed_dummy_owners(cursor)

    conn.commit()
    conn.close()
    print("✅ Database initialized")

# -----------------------------
# Seed dummy data for POC
# -----------------------------
def seed_dummy_owners(cursor):
    dummy_owners = [
        # (owner_id, line_user_id, name, phone)
        # ⚠️ Replace line_user_id with real LINE userId
        # after owner adds bot and sends LINK:owner_id
        ("owner001", "", "Alice Smith",  "+66-81-000-0001"),
        ("owner002", "", "Bob Johnson",  "+66-81-000-0002"),
        ("owner003", "", "Charlie Brown", "+66-81-000-0003"),
    ]

    for owner in dummy_owners:
        cursor.execute("""
            INSERT OR IGNORE INTO fleet_owners (owner_id, line_user_id, name, phone)
            VALUES (?, ?, ?, ?)
        """, owner)

# -----------------------------
# Save / Update owner LINE userId
# -----------------------------
def save_owner(owner_id, line_user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fleet_owners (owner_id, line_user_id)
        VALUES (?, ?)
        ON CONFLICT(owner_id) DO UPDATE SET line_user_id = excluded.line_user_id
    """, (owner_id, line_user_id))
    conn.commit()
    conn.close()
    print(f"✅ Saved: {owner_id} → {line_user_id}")

# -----------------------------
# Get LINE userId by owner_id
# -----------------------------
def get_line_user_id(owner_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT line_user_id FROM fleet_owners WHERE owner_id = ?",
        (owner_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# -----------------------------
# Get all owners
# -----------------------------
def get_all_owners():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT owner_id, line_user_id, name, phone FROM fleet_owners")
    rows = cursor.fetchall()
    conn.close()
    return rows

# -----------------------------
# Save location history
# -----------------------------
def save_location(owner_id, vehicle_id, driver_name, latitude, longitude, speed, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO location_history
            (owner_id, vehicle_id, driver_name, latitude, longitude, speed, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (owner_id, vehicle_id, driver_name, latitude, longitude, speed, status))
    conn.commit()
    conn.close()

# -----------------------------
# Get location history by owner
# -----------------------------
def get_location_history(owner_id, limit=10):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT vehicle_id, driver_name, latitude, longitude, speed, status, sent_at
        FROM location_history
        WHERE owner_id = ?
        ORDER BY sent_at DESC
        LIMIT ?
    """, (owner_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# -----------------------------
# Print all tables (for debugging)
# -----------------------------
def print_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("\n📋 Fleet Owners:")
    print(f"{'owner_id':<12} {'line_user_id':<25} {'name':<15} {'phone'}")
    print("-" * 70)
    cursor.execute("SELECT owner_id, line_user_id, name, phone FROM fleet_owners")
    for row in cursor.fetchall():
        print(f"{row[0]:<12} {row[1]:<25} {row[2]:<15} {row[3]}")

    print("\n📍 Location History (last 10):")
    print(f"{'owner_id':<12} {'vehicle':<10} {'driver':<15} {'lat':<10} {'lng':<10} {'speed':<8} {'status':<10} {'sent_at'}")
    print("-" * 90)
    cursor.execute("""
        SELECT owner_id, vehicle_id, driver_name, latitude, longitude, speed, status, sent_at
        FROM location_history ORDER BY sent_at DESC LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"{row[0]:<12} {row[1]:<10} {row[2]:<15} {row[3]:<10} {row[4]:<10} {row[5]:<8} {row[6]:<10} {row[7]}")

    conn.close()