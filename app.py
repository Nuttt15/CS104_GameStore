from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3
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

    conn.close()

    return render_template(
        'index.html',
        total_products=total_products,
        total_stock=total_stock
    )


@app.route('/products')
def products():
    conn = get_db_connection()
    selected_category = request.args.get('category', 'all')
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

    if selected_category != 'all':
        sql += ' WHERE products.category_id = ?'
        params.append(selected_category)

    sql += ' ORDER BY products.product_id DESC'

    products = conn.execute(sql, params).fetchall()

    conn.close()

    return render_template(
        'products.html',
        products=products,
        categories=categories,
        selected_category=selected_category
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


prepare_app_storage()


if __name__ == '__main__':
    app.run(debug=True)
