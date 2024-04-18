from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techcompare.db'
db = SQLAlchemy(app)

class Product(db.Model):
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Review(db.Model):
    review_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    date = db.Column(db.DateTime)



with app.app_context():
    db.create_all()

@app.route('/products')
def get_products():
    response = requests.get("https://fakestoreapi.com/products")
    products = response.json()
    return jsonify(products)

@app.route('/search')
def search_products():
    # Fetch query parameters
    query = request.args.get('query', '').lower()
    category = request.args.get('category', '').lower()
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    sort_order = request.args.get('sort', 'asc')

    # Fetch all products
    response = requests.get("https://fakestoreapi.com/products")
    products = response.json()

    # Filter by search query
    if query:
        products = [product for product in products if query in product['title'].lower()]

    # Filter by category
    if category:
        products = [product for product in products if product['category'].lower() == category]

    # Filter by price range
    if price_min is not None:
        products = [product for product in products if product['price'] >= price_min]
    if price_max is not None:
        products = [product for product in products if product['price'] <= price_max]

    # Sort products
    if sort_order == 'desc':
        products.sort(key=lambda x: x['price'], reverse=True)
    else:
        products.sort(key=lambda x: x['price'])

    return jsonify(products)


@app.route('/compare')
def compare_products():
    # Fetch product IDs from query parameters
    product_ids = request.args.getlist('ids', type=int)
    sort_order = request.args.get('sort', 'rating')  # Default sort by rating

    if not product_ids or len(product_ids) < 2:
        return jsonify({'error': 'At least two product IDs are required for comparison'}), 400

    # Fetch products from the API
    response = requests.get(f"https://fakestoreapi.com/products")
    all_products = response.json()

    # Filter products to only include those with matching IDs
    products_to_compare = [product for product in all_products if product['id'] in product_ids]

    if not products_to_compare:
        return jsonify({'error': 'No products found for the given IDs'}), 404

    # Check if all products are in the same category
    first_product_category = products_to_compare[0]['category']
    if not all(product['category'] == first_product_category for product in products_to_compare):
        return jsonify({'error': 'All products must be in the same category for comparison'}), 400

    # Compute score for each product for internal use
    for product in products_to_compare:
        rating = product.get('rating', {})
        product['score'] = rating.get('count', 0) * rating.get('rate', 0)

    # Sort products based on the specified order
    if sort_order == 'price':
        products_to_compare.sort(key=lambda x: (x['price'], -x.get('score', 0)))
    else:
        products_to_compare.sort(key=lambda x: (-x.get('score', 0), x['price']))

    # Remove the 'score' key from the products before returning
    for product in products_to_compare:
        product.pop('score', None)

    return jsonify(products_to_compare)

@app.route('/reviews/<int:product_id>', methods=['GET'])
def get_reviews(product_id):
    reviews = Review.query.filter_by(product_id=product_id).all()
    review_data = [{
        'user_id': review.user_id,
        'rating': review.rating,
        'comment': review.comment,
        'date': review.date.isoformat()
    } for review in reviews]
    return jsonify(review_data)

@app.route('/reviews', methods=['POST'])
def add_review():
    data = request.get_json()
    if not data or not all(key in data for key in ['product_id', 'user_id', 'rating', 'comment']):
        return jsonify({'error': 'Missing data'}), 400

    new_review = Review(
        product_id=data['product_id'],
        user_id=data['user_id'],
        rating=data['rating'],
        comment=data['comment'],
        date=datetime.utcnow()
    )
    db.session.add(new_review)
    db.session.commit()
    return jsonify({'message': 'Review added successfully'}), 201


if __name__ == '__main__':
    app.run(debug=True)
