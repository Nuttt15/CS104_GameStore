import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# Customers
cur.execute('''
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT UNIQUE
)
''')

# Categories
cur.execute('''
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
)
''')

# Products
cur.execute('''
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    image_filename TEXT,
    category_id INTEGER,
    FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
)
''')

# Orders
cur.execute('''
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    order_date TEXT,
    total_price REAL,
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
)
''')

# Payments
cur.execute('''
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    payment_method TEXT,
    payment_status TEXT,
    payment_date TEXT,
    FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
)
''')

# Insert categories
categories = [
    ('Gaming Gear',),
    ('Console Game',),
    ('PC Game',)
]

cur.executemany(
    'INSERT OR IGNORE INTO categories (category_name) VALUES (?)',
    categories
)

conn.commit()
conn.close()

print("Database created successfully!")
