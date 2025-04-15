"""
Helper functions for the Decentralized Cloud Resource Gateway
"""
import json
from datetime import datetime, timedelta
from flask import flash, redirect, url_for
from functools import wraps
from flask_login import current_user


def admin_required(f):
    """Decorator for routes that require admin access"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username != 'admin':
            flash('Admin access required for this page.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return '-'
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def calculate_duration(start_time, end_time=None):
    """Calculate duration between two timestamps"""
    if not end_time:
        end_time = datetime.utcnow()

    delta = end_time - start_time

    # Format as hours and minutes
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)

    return f"{int(hours)}h {int(minutes)}m"


def parse_resource_specs(specifications_json):
    """Parse JSON specifications into a readable format"""
    if not specifications_json:
        return {}

    try:
        specs = json.loads(specifications_json)
        return specs
    except json.JSONDecodeError:
        return {}


def format_credits(credits):
    """Format credits value for display"""
    return f"{credits:.2f}"


def get_resource_usage_stats(resources, days=30):
    """Calculate resource usage statistics for a set of resources"""
    from models.transaction import Transaction
    from app import db
    from sqlalchemy import func

    stats = {}
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    for resource in resources:
        # Get usage time
        usage_data = db.session.query(
            func.sum(
                func.julianday(Transaction.end_time or datetime.utcnow()) -
                func.julianday(Transaction.start_time)
            ) * 24  # Convert to hours
        ).filter(
            Transaction.resource_id == resource.id,
            Transaction.start_time >= cutoff_date
        ).scalar() or 0

        # Get credit earnings
        earnings = db.session.query(
            func.sum(Transaction.credits)
        ).filter(
            Transaction.resource_id == resource.id,
            Transaction.start_time >= cutoff_date
        ).scalar() or 0

        # Get utilization percentage (hours used / hours available)
        total_hours = days * 24
        utilization = (usage_data / total_hours) * 100 if total_hours > 0 else 0

        stats[resource.id] = {
            'hours_used': round(usage_data, 2),
            'credits_earned': round(earnings, 2),
            'utilization': round(utilization, 2)
        }

    return stats


def validate_resource_params(form_data):
    """Validate resource parameters"""
    errors = []

    # Check required fields
    required_fields = ['name', 'type', 'capacity', 'credits_per_hour']
    for field in required_fields:
        if not form_data.get(field):
            errors.append(f"Field '{field}' is required")

    # Check numeric fields
    try:
        capacity = float(form_data.get('capacity', 0))
        if capacity <= 0:
            errors.append("Capacity must be greater than zero")
    except ValueError:
        errors.append("Capacity must be a number")

    try:
        credits = float(form_data.get('credits_per_hour', 0))
        if credits < 0:
            errors.append("Credits per hour cannot be negative")
    except ValueError:
        errors.append("Credits per hour must be a number")

    return errors