from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    resources = db.relationship('Resource', backref='owner', lazy='dynamic')
    credits = db.Column(db.Float, default=100.0)  # Starting credits

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # CPU, GPU, Storage, etc.
    capacity = db.Column(db.Float, nullable=False)  # Amount of resource
    status = db.Column(db.String(20), default='available')  # available, in_use, offline
    credits_per_hour = db.Column(db.Float, nullable=False)  # Cost in credits
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    borrowed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'))
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    consumer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    credits = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled

    resource = db.relationship('Resource')
    provider = db.relationship('User', foreign_keys=[provider_id])
    consumer = db.relationship('User', foreign_keys=[consumer_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user_exists = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
        if user_exists:
            flash('Username or email already exists.')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        return redirect(next_page)

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    my_resources = Resource.query.filter_by(user_id=current_user.id).all()
    borrowed_resources = Resource.query.filter_by(borrowed_by=current_user.id).all()
    my_transactions = Transaction.query.filter_by(consumer_id=current_user.id).all()
    provided_transactions = Transaction.query.filter_by(provider_id=current_user.id).all()

    return render_template('dashboard.html',
                           my_resources=my_resources,
                           borrowed_resources=borrowed_resources,
                           my_transactions=my_transactions,
                           provided_transactions=provided_transactions)


@app.route('/resource_pool')
@login_required
def resource_pool():
    resources = Resource.query.filter_by(status='available').all()
    return render_template('resource_pool.html', resources=resources)


@app.route('/add_resource', methods=['POST'])
@login_required
def add_resource():
    name = request.form.get('name')
    resource_type = request.form.get('type')
    capacity = float(request.form.get('capacity'))
    credits_per_hour = float(request.form.get('credits_per_hour'))

    resource = Resource(name=name,
                        type=resource_type,
                        capacity=capacity,
                        credits_per_hour=credits_per_hour,
                        owner=current_user)

    db.session.add(resource)
    db.session.commit()

    flash('Resource added successfully!')
    return redirect(url_for('dashboard'))


@app.route('/borrow_resource/<int:resource_id>', methods=['POST'])
@login_required
def borrow_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    # Check if resource is available
    if resource.status != 'available':
        flash('This resource is no longer available.')
        return redirect(url_for('resource_pool'))

    # Check if user has enough credits
    hours = float(request.form.get('hours', 1))
    total_cost = resource.credits_per_hour * hours

    if current_user.credits < total_cost:
        flash('You do not have enough credits.')
        return redirect(url_for('resource_pool'))

    # Create transaction
    transaction = Transaction(
        resource_id=resource.id,
        provider_id=resource.user_id,
        consumer_id=current_user.id,
        credits=total_cost
    )

    # Update resource status
    resource.status = 'in_use'
    resource.borrowed_by = current_user.id

    # Update user credits
    current_user.credits -= total_cost
    resource.owner.credits += total_cost

    db.session.add(transaction)
    db.session.commit()

    flash('Resource borrowed successfully!')
    return redirect(url_for('dashboard'))


@app.route('/return_resource/<int:resource_id>', methods=['POST'])
@login_required
def return_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if resource.borrowed_by != current_user.id:
        flash('You cannot return this resource.')
        return redirect(url_for('dashboard'))

    # Find the active transaction
    transaction = Transaction.query.filter_by(
        resource_id=resource.id,
        consumer_id=current_user.id,
        status='active'
    ).first()

    if transaction:
        transaction.end_time = datetime.utcnow()
        transaction.status = 'completed'

    # Reset resource status
    resource.status = 'available'
    resource.borrowed_by = None

    db.session.commit()

    flash('Resource returned successfully!')
    return redirect(url_for('dashboard'))


@app.route('/api/resources', methods=['GET'])
@login_required
def api_resources():
    resources = Resource.query.filter_by(status='available').all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'type': r.type,
        'capacity': r.capacity,
        'credits_per_hour': r.credits_per_hour,
        'owner': User.query.get(r.user_id).username
    } for r in resources])


# Create database tables if they don't exist
with app.app_context():
    db.create_all()


# Add sample data if database is empty
def create_sample_data():
    with app.app_context():
        if User.query.count() == 0:
            # Create sample users
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('password')
            admin.credits = 500

            user1 = User(username='provider1', email='provider1@example.com')
            user1.set_password('password')
            user1.credits = 300

            user2 = User(username='consumer1', email='consumer1@example.com')
            user2.set_password('password')
            user2.credits = 200

            db.session.add_all([admin, user1, user2])
            db.session.commit()

            # Create sample resources
            resources = [
                Resource(name='High CPU Server', type='CPU', capacity=16.0,
                         credits_per_hour=10.0, user_id=user1.id),
                Resource(name='GPU Computing Node', type='GPU', capacity=2.0,
                         credits_per_hour=25.0, user_id=user1.id),
                Resource(name='Storage Array', type='Storage', capacity=500.0,
                         credits_per_hour=5.0, user_id=admin.id),
                Resource(name='Memory Node', type='RAM', capacity=128.0,
                         credits_per_hour=8.0, user_id=admin.id)
            ]

            db.session.add_all(resources)
            db.session.commit()


create_sample_data()

if __name__ == '__main__':
    app.run(debug=True)