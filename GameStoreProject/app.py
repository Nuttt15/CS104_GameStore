from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


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

    products = conn.execute('''
        SELECT
            products.product_id,
            products.product_name,
            products.price,
            products.stock,
            products.category_id,
            categories.category_name
        FROM products
        LEFT JOIN categories
            ON products.category_id = categories.category_id
        ORDER BY products.product_id DESC
    ''').fetchall()

    conn.close()

    return render_template('products.html', products=products)


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories').fetchall()

    if request.method == 'POST':
        name = request.form['product_name']
        price = request.form['price']
        stock = request.form['stock']
        category_id = request.form['category_id']

        conn.execute('''
            INSERT INTO products
            (product_name, price, stock, category_id)
            VALUES (?, ?, ?, ?)
        ''', (name, price, stock, category_id))

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

    categories = conn.execute('''
        SELECT * FROM categories
    ''').fetchall()

    if request.method == 'POST':
        name = request.form['product_name']
        price = request.form['price']
        stock = request.form['stock']
        category_id = request.form['category_id']

        conn.execute('''
            UPDATE products
            SET product_name = ?,
                price = ?,
                stock = ?,
                category_id = ?
            WHERE product_id = ?
        ''', (name, price, stock, category_id, id))

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


if __name__ == '__main__':
    app.run(debug=True)