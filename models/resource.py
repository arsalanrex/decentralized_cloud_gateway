"""
Resource model for the Decentralized Cloud Resource Gateway
"""
from datetime import datetime
from app import db


class Resource(db.Model):
    """
    Resource model representing a computing resource in the sharing network
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # CPU, GPU, Storage, etc.
    capacity = db.Column(db.Float, nullable=False)  # Amount of resource
    status = db.Column(db.String(20), default='available')  # available, in_use, offline
    credits_per_hour = db.Column(db.Float, nullable=False)  # Cost in credits

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    borrowed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional resource specifications
    specifications = db.Column(db.Text, nullable=True)  # JSON string with detailed specs

    def is_available(self):
        """Check if resource is available for use"""
        return self.status == 'available'

    def assign_to_user(self, user_id):
        """Assign this resource to a user"""
        if not self.is_available():
            return False

        self.status = 'in_use'
        self.borrowed_by = user_id
        self.last_active = datetime.utcnow()
        return True

    def release(self):
        """Release this resource back to the pool"""
        self.status = 'available'
        self.borrowed_by = None
        self.last_active = datetime.utcnow()
        return True

    def take_offline(self):
        """Take this resource offline"""
        self.status = 'offline'
        self.last_active = datetime.utcnow()
        return True

    def __repr__(self):
        return f'<Resource {self.name} ({self.type})>'