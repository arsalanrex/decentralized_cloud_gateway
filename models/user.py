"""
User model for the Decentralized Cloud Resource Gateway
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """
    User model representing a participant in the resource sharing network
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    credits = db.Column(db.Float, default=100.0)  # Starting credits
    reputation = db.Column(db.Float, default=0.0)  # User reputation score

    # Relationships
    # In models/user.py
    resources = db.relationship('Resource',
                                foreign_keys='Resource.user_id',
                                backref='owner',
                                lazy='dynamic')

    borrowed_resources = db.relationship('Resource',
                                         foreign_keys='Resource.borrowed_by',
                                         backref='borrower',
                                         lazy='dynamic')

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def get_resources(self):
        """Get all resources owned by this user"""
        return self.resources.all()

    def get_active_resources(self):
        """Get available resources owned by this user"""
        return self.resources.filter_by(status='available').all()

    def get_borrowed_resources(self):
        """Get resources this user is currently borrowing"""
        from models.resource import Resource
        return Resource.query.filter_by(borrowed_by=self.id).all()

    def __repr__(self):
        return f'<User {self.username}>'