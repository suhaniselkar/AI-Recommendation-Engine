
from pathlib import Path
import sqlite3
import uuid

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "recommendations.db"


# ==========================================
# DATABASE CONNECTION AND TABLE CREATION
# ==========================================

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --------------------------------------
    # INTERACTIONS TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            rating INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------
    # CUSTOMERS TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------
    # AUTHENTICATION SESSIONS TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------
    # WISHLIST TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        )
    """)

    # --------------------------------------
    # SHOPPING CART TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1
                CHECK(quantity > 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        )
    """)

    # --------------------------------------
    # ORDERS TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------
    # ORDER ITEMS TABLE
    # --------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_title TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            item_total REAL NOT NULL,
            FOREIGN KEY(order_id)
                REFERENCES orders(order_id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    return conn


# ==========================================
# INTERACTION FUNCTIONS
# ==========================================

def save_interaction(user_id, product_id, event_type, rating=None):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO interactions
            (user_id, product_id, event_type, rating)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, product_id, event_type, rating)
        )
        conn.commit()
    finally:
        conn.close()


def get_saved_interactions():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT user_id, product_id, event_type, rating
            FROM interactions
            """
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_customer_interactions(user_id, limit=50):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, product_id, event_type,
                   rating, created_at
            FROM interactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


# ==========================================
# CUSTOMER FUNCTIONS
# ==========================================

def create_customer(user_id, name, email, password_hash):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO customers
            (user_id, name, email, password_hash)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, email, password_hash)
        )
        conn.commit()
    finally:
        conn.close()


def find_customer_by_email(email):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT user_id, name, email, password_hash
            FROM customers
            WHERE email=?
            """,
            (email,)
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def get_customer_by_id(user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT user_id, name, email, created_at
            FROM customers
            WHERE user_id=?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def update_customer_profile(user_id, name, email):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE customers
            SET name=?, email=?
            WHERE user_id=?
            """,
            (name, email, user_id)
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT user_id, name, email, created_at
            FROM customers
            WHERE user_id=?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def update_customer_password(user_id, password_hash):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE customers
            SET password_hash=?
            WHERE user_id=?
            """,
            (password_hash, user_id)
        )
        conn.commit()

        return cursor.rowcount > 0
    finally:
        conn.close()


# ==========================================
# AUTHENTICATION SESSION FUNCTIONS
# ==========================================

def create_session(token, user_id):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO auth_sessions (token, user_id)
            VALUES (?, ?)
            """,
            (token, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def find_session(token):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT c.user_id, c.name, c.email
            FROM auth_sessions s
            JOIN customers c ON c.user_id=s.user_id
            WHERE s.token=?
            """,
            (token,)
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token):
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM auth_sessions WHERE token=?",
            (token,)
        )
        conn.commit()
    finally:
        conn.close()


def delete_customer_sessions(user_id):
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM auth_sessions WHERE user_id=?",
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


# ==========================================
# WISHLIST FUNCTIONS
# ==========================================

def add_to_wishlist(user_id, product_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO wishlist
            (user_id, product_id)
            VALUES (?, ?)
            """,
            (user_id, product_id)
        )
        conn.commit()

        return cursor.rowcount > 0
    finally:
        conn.close()


def get_customer_wishlist(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, product_id, created_at
            FROM wishlist
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def remove_from_wishlist(user_id, product_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            DELETE FROM wishlist
            WHERE user_id=? AND product_id=?
            """,
            (user_id, product_id)
        )
        conn.commit()

        return cursor.rowcount > 0
    finally:
        conn.close()


# ==========================================
# SHOPPING CART FUNCTIONS
# ==========================================

def add_to_cart(user_id, product_id, quantity=1):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO cart_items
            (user_id, product_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, product_id)
            DO UPDATE SET
                quantity = cart_items.quantity + excluded.quantity,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, product_id, quantity)
        )
        conn.commit()

        return True
    finally:
        conn.close()


def get_customer_cart(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, product_id, quantity,
                   created_at, updated_at
            FROM cart_items
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_cart_quantity(user_id, product_id, quantity):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE cart_items
            SET quantity=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE user_id=? AND product_id=?
            """,
            (quantity, user_id, product_id)
        )
        conn.commit()

        return cursor.rowcount > 0
    finally:
        conn.close()


def remove_from_cart(user_id, product_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            DELETE FROM cart_items
            WHERE user_id=? AND product_id=?
            """,
            (user_id, product_id)
        )
        conn.commit()

        return cursor.rowcount > 0
    finally:
        conn.close()


def clear_customer_cart(user_id):
    conn = get_connection()
    try:
        conn.execute(
            """
            DELETE FROM cart_items
            WHERE user_id=?
            """,
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


# ==========================================
# ORDER MANAGEMENT FUNCTIONS
# ==========================================

def create_order(user_id, items, total_amount):
    conn = get_connection()

    try:
        order_id = "ORD-" + uuid.uuid4().hex[:12].upper()

        conn.execute(
            """
            INSERT INTO orders
            (order_id, user_id, total_amount, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (order_id, user_id, total_amount)
        )

        for item in items:
            conn.execute(
                """
                INSERT INTO order_items
                (
                    order_id,
                    product_id,
                    product_title,
                    quantity,
                    unit_price,
                    item_total
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["product_title"],
                    item["quantity"],
                    item["unit_price"],
                    item["item_total"]
                )
            )

        # Clear cart only after all order records are inserted
        conn.execute(
            "DELETE FROM cart_items WHERE user_id=?",
            (user_id,)
        )

        conn.commit()

        return order_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_customer_orders(user_id):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id=?
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_order_by_id(order_id, user_id):
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM orders
            WHERE order_id=? AND user_id=?
            """,
            (order_id, user_id)
        ).fetchone()

        if not row:
            return None

        order = dict(row)

        items = conn.execute(
            """
            SELECT *
            FROM order_items
            WHERE order_id=?
            ORDER BY id ASC
            """,
            (order_id,)
        ).fetchall()

        order["items"] = [dict(item) for item in items]

        return order

    finally:
        conn.close()


def cancel_customer_order(order_id, user_id):
    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            UPDATE orders
            SET status='cancelled',
                updated_at=CURRENT_TIMESTAMP
            WHERE order_id=?
              AND user_id=?
              AND status='pending'
            """,
            (order_id, user_id)
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:
        conn.close()
