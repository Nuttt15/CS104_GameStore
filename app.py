from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

app = Flask(__name__)
app.config['DATABASE'] = Path(app.root_path) / 'database.db'
app.config['UPLOAD_FOLDER'] = Path(app.root_path) / 'static' / 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    )


def save_product_image(file):
    if not file or file.filename == '' or not allowed_file(file.filename):
        return None

    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    new_filename = f'{uuid4().hex}.{extension}'
    file.save(app.config['UPLOAD_FOLDER'] / new_filename)

    return new_filename


def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def prepare_app_storage():
    app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    products_table = conn.execute('''
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = 'products'
    ''').fetchone()

    if products_table is None:
        conn.close()
        return

    columns = conn.execute('PRAGMA table_info(products)').fetchall()
    column_names = [column['name'] for column in columns]

    if 'image_filename' not in column_names:
        conn.execute('ALTER TABLE products ADD COLUMN image_filename TEXT')
        conn.commit()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id)
                REFERENCES orders(order_id),
            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
        )
    ''')
    conn.commit()

    conn.close()


def get_categories(conn):
    return conn.execute('''
        SELECT * FROM categories
        ORDER BY
            CASE category_name
                WHEN 'Gaming Gear' THEN 1
                WHEN 'Console Game' THEN 2
                WHEN 'PC Game' THEN 3
                ELSE 4
            END
    ''').fetchall()


@app.route('/')
def index():
    conn = get_db_connection()

    total_products = conn.execute('''
        SELECT COUNT(*) AS total FROM products
    ''').fetchone()['total']

    total_stock = conn.execute('''
        SELECT COALESCE(SUM(stock), 0) AS total FROM products
    ''').fetchone()['total']

    total_customers = conn.execute('''
        SELECT COUNT(*) AS total FROM customers
    ''').fetchone()['total']

    total_orders = conn.execute('''
        SELECT COUNT(*) AS total FROM orders
    ''').fetchone()['total']

    conn.close()

    return render_template(
        'index.html',
        total_products=total_products,
        total_stock=total_stock,
        total_customers=total_customers,
        total_orders=total_orders
    )


@app.route('/products')
def products():
    conn = get_db_connection()
    selected_category = request.args.get('category', 'all')
    search_query = request.args.get('q', '').strip()
    categories = get_categories(conn)

    sql = '''
        SELECT
            products.product_id,
            products.product_name,
            products.price,
            products.stock,
            products.category_id,
            products.image_filename,
            categories.category_name
        FROM products
        LEFT JOIN categories
            ON products.category_id = categories.category_id
    '''
    params = []
    conditions = []

    if selected_category != 'all':
        conditions.append('products.category_id = ?')
        params.append(selected_category)

    if search_query:
        conditions.append('''
            (
                products.product_name LIKE ?
                OR categories.category_name LIKE ?
            )
        ''')
        search_text = f'%{search_query}%'
        params.extend([search_text, search_text])

    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)

    sql += ' ORDER BY products.product_id DESC'

    products = conn.execute(sql, params).fetchall()

    conn.close()

    return render_template(
        'products.html',
        products=products,
        categories=categories,
        selected_category=selected_category,
        search_query=search_query
    )


@app.route('/category/<int:category_id>')
def products_by_category(category_id):
    return redirect(url_for('products', category=category_id))


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = get_db_connection()
    categories = get_categories(conn)

    if request.method == 'POST':
        name = request.form['product_name']
        price = request.form['price']
        stock = request.form['stock']
        category_id = request.form['category_id']
        image_filename = save_product_image(request.files.get('product_image'))

        conn.execute('''
            INSERT INTO products
            (product_name, price, stock, category_id, image_filename)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, price, stock, category_id, image_filename))

        conn.commit()
        conn.close()

        return redirect('/products')

    conn.close()

    return render_template('add_product.html', categories=categories)


@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    conn = get_db_connection()

    product = conn.execute('''
        SELECT * FROM products
        WHERE product_id = ?
    ''', (id,)).fetchone()

    categories = get_categories(conn)

    if request.method == 'POST':
        name = request.form['product_name']
        price = request.form['price']
        stock = request.form['stock']
        category_id = request.form['category_id']
        image_filename = save_product_image(request.files.get('product_image'))

        if image_filename is None:
            image_filename = product['image_filename']

        conn.execute('''
            UPDATE products
            SET product_name = ?,
                price = ?,
                stock = ?,
                category_id = ?,
                image_filename = ?
            WHERE product_id = ?
        ''', (name, price, stock, category_id, image_filename, id))

        conn.commit()
        conn.close()

        return redirect('/products')

    conn.close()

    return render_template(
        'edit_product.html',
        product=product,
        categories=categories
    )


@app.route('/delete_product/<int:id>')
def delete_product(id):
    conn = get_db_connection()

    conn.execute('''
        DELETE FROM products
        WHERE product_id = ?
    ''', (id,))

    conn.commit()
    conn.close()

    return redirect('/products')


@app.route('/customers')
def customers():
    conn = get_db_connection()

    customers = conn.execute('''
        SELECT * FROM customers
        ORDER BY customer_id DESC
    ''').fetchall()

    conn.close()

    return render_template('customers.html', customers=customers)


@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    error = None

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']

        conn = get_db_connection()

        try:
            conn.execute('''
                INSERT INTO customers (name, phone, email)
                VALUES (?, ?, ?)
            ''', (name, phone, email))
            conn.commit()
            conn.close()

            return redirect('/customers')
        except sqlite3.IntegrityError:
            error = 'This email is already used.'
            conn.close()

    return render_template('add_customer.html', error=error)


@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    conn = get_db_connection()

    customer = conn.execute('''
        SELECT * FROM customers
        WHERE customer_id = ?
    ''', (id,)).fetchone()

    error = None

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']

        try:
            conn.execute('''
                UPDATE customers
                SET name = ?,
                    phone = ?,
                    email = ?
                WHERE customer_id = ?
            ''', (name, phone, email, id))
            conn.commit()
            conn.close()

            return redirect('/customers')
        except sqlite3.IntegrityError:
            error = 'This email is already used.'

    conn.close()

    return render_template(
        'edit_customer.html',
        customer=customer,
        error=error
    )


@app.route('/delete_customer/<int:id>')
def delete_customer(id):
    conn = get_db_connection()

    conn.execute('''
        DELETE FROM customers
        WHERE customer_id = ?
    ''', (id,))

    conn.commit()
    conn.close()

    return redirect('/customers')


@app.route('/orders')
def orders():
    conn = get_db_connection()

    orders = conn.execute('''
        SELECT
            orders.order_id,
            orders.order_date,
            orders.total_price,
            customers.name AS customer_name,
            products.product_name,
            order_items.quantity
        FROM orders
        LEFT JOIN customers
            ON orders.customer_id = customers.customer_id
        LEFT JOIN order_items
            ON orders.order_id = order_items.order_id
        LEFT JOIN products
            ON order_items.product_id = products.product_id
        ORDER BY orders.order_id DESC
    ''').fetchall()

    conn.close()

    return render_template('orders.html', orders=orders)


@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    conn = get_db_connection()
    error = None

    customers = conn.execute('''
        SELECT * FROM customers
        ORDER BY name
    ''').fetchall()

    products = conn.execute('''
        SELECT * FROM products
        WHERE stock > 0
        ORDER BY product_name
    ''').fetchall()

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])

        product = conn.execute('''
            SELECT * FROM products
            WHERE product_id = ?
        ''', (product_id,)).fetchone()

        if product is None:
            error = 'Product not found.'
        elif quantity <= 0:
            error = 'Quantity must be more than 0.'
        elif quantity > product['stock']:
            error = 'Not enough stock for this order.'
        else:
            total_price = product['price'] * quantity
            order_date = datetime.now().strftime('%Y-%m-%d %H:%M')

            cursor = conn.execute('''
                INSERT INTO orders (customer_id, order_date, total_price)
                VALUES (?, ?, ?)
            ''', (customer_id, order_date, total_price))

            order_id = cursor.lastrowid

            conn.execute('''
                INSERT INTO order_items
                (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, product_id, quantity, product['price']))

            conn.execute('''
                UPDATE products
                SET stock = stock - ?
                WHERE product_id = ?
            ''', (quantity, product_id))

            conn.commit()
            conn.close()

            return redirect('/orders')

    conn.close()

    return render_template(
        'add_order.html',
        customers=customers,
        products=products,
        error=error
    )


prepare_app_storage()


if __name__ == '__main__':
    app.run(debug=True)
