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
            owner_mobile   TEXT PRIMARY KEY,
            line_user_id   TEXT NOT NULL,
            created_date   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Location history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_mobile  TEXT NOT NULL,
            vehicle_id    TEXT NOT NULL,
            driver_name   TEXT,
            latitude      REAL NOT NULL,
            longitude     REAL NOT NULL,
            speed         REAL DEFAULT 0,
            status        TEXT DEFAULT 'unknown',
            sent_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    print("✅ Database initialized")


# -----------------------------
# Save / Update owner link
# -----------------------------
def save_owner(owner_mobile, line_user_id):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO fleet_owners (owner_mobile, line_user_id)
        VALUES (?, ?)
        ON CONFLICT(owner_mobile)
        DO UPDATE SET line_user_id = excluded.line_user_id
    """, (owner_mobile, line_user_id))

    conn.commit()
    conn.close()

    print(f"✅ Linked: {owner_mobile} → {line_user_id}")


# -----------------------------
# Get LINE userId by mobile
# -----------------------------
def get_line_user_id(owner_mobile):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT line_user_id FROM fleet_owners WHERE owner_mobile = ?",
        (owner_mobile,)
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

    cursor.execute("""
        SELECT owner_mobile, line_user_id, created_date
        FROM fleet_owners
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Save location history
# -----------------------------
def save_location(owner_mobile, vehicle_id, driver_name, latitude, longitude, speed, status):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO location_history
        (owner_mobile, vehicle_id, driver_name, latitude, longitude, speed, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (owner_mobile, vehicle_id, driver_name, latitude, longitude, speed, status))

    conn.commit()
    conn.close()


# -----------------------------
# Get location history
# -----------------------------
def get_location_history(owner_mobile, limit=10):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT vehicle_id, driver_name, latitude, longitude, speed, status, sent_at
        FROM location_history
        WHERE owner_mobile = ?
        ORDER BY sent_at DESC
        LIMIT ?
    """, (owner_mobile, limit))

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Debug print database
# -----------------------------
def print_db():

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("\n📋 Fleet Owners:")
    print(f"{'mobile':<15} {'line_user_id':<30} {'created_date'}")
    print("-" * 70)

    cursor.execute("""
        SELECT owner_mobile, line_user_id, created_date
        FROM fleet_owners
    """)

    for row in cursor.fetchall():
        print(f"{row[0]:<15} {row[1]:<30} {row[2]}")

    print("\n📍 Location History (last 10):")

    print(f"{'mobile':<15} {'vehicle':<10} {'driver':<15} {'lat':<10} {'lng':<10} {'speed':<8} {'status':<10} {'sent_at'}")
    print("-" * 100)

    cursor.execute("""
        SELECT owner_mobile, vehicle_id, driver_name, latitude, longitude, speed, status, sent_at
        FROM location_history
        ORDER BY sent_at DESC
        LIMIT 10
    """)

    for row in cursor.fetchall():
        print(f"{row[0]:<15} {row[1]:<10} {row[2]:<15} {row[3]:<10} {row[4]:<10} {row[5]:<8} {row[6]:<10} {row[7]}")

    conn.close()