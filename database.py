import sqlite3
import json
from config import Config
from utils.logger import log

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        log.info("Initializing SQLite Database Tables...")
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Categories
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    enabled INTEGER DEFAULT 1,
                    position INTEGER DEFAULT 0
                )
            """)
            
            # Products
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    image_url TEXT,
                    visibility INTEGER DEFAULT 1,
                    type TEXT NOT NULL,
                    stock_type TEXT NOT NULL,
                    stock_count INTEGER DEFAULT 0,
                    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)
            
            # Variants
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS variants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    price REAL NOT NULL,
                    discount REAL DEFAULT 0.0,
                    availability INTEGER DEFAULT 1,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            
            # Custom Fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    label TEXT NOT NULL,
                    placeholder TEXT,
                    is_required INTEGER DEFAULT 1,
                    min_length INTEGER DEFAULT 1,
                    max_length INTEGER DEFAULT 100,
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            
            # Payment Methods
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1
                )
            """)

            # Orders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER,
                    variant_id INTEGER,
                    custom_inputs TEXT, -- JSON structure
                    price REAL,
                    payment_method_id INTEGER,
                    payment_status TEXT DEFAULT 'Pending',
                    order_status TEXT DEFAULT 'Pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id),
                    FOREIGN KEY(variant_id) REFERENCES variants(id),
                    FOREIGN KEY(payment_method_id) REFERENCES payment_methods(id)
                )
            """)

            # Tickets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER,
                    channel_id INTEGER UNIQUE,
                    status TEXT DEFAULT 'Open',
                    close_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            """)

            # Reviews
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER,
                    order_id INTEGER,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    review_text TEXT,
                    anonymous INTEGER DEFAULT 0,
                    approved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id),
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                )
            """)

            # Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    # Query helper functions
    def execute(self, query, params=()):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetch_all(self, query, params=()):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def fetch_one(self, query, params=()):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

db = Database()
