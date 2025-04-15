"""
Resource matching service for finding optimal resources
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from models.resource import Resource
from models.user import User


class ResourceMatcher:
    """
    Handles resource matching algorithms for connecting users with available resources
    """

    @staticmethod
    def find_available_resources(resource_type=None, min_capacity=None, max_credits=None, db_session=None):
        """
        Find available resources based on criteria

        Args:
            resource_type: Type of resource (CPU, GPU, etc)
            min_capacity: Minimum capacity required
            max_credits: Maximum credits per hour
            db_session: Database session

        Returns:
            List of matching resources
        """
        query = db_session.query(Resource).filter(Resource.status == 'available')

        if resource_type:
            query = query.filter(Resource.type == resource_type)

        if min_capacity:
            query = query.filter(Resource.capacity >= min_capacity)

        if max_credits:
            query = query.filter(Resource.credits_per_hour <= max_credits)

        return query.all()

    @staticmethod
    def recommend_resources(user_id, db_session=None):
        """
        Recommend resources based on user's past usage

        Args:
            user_id: ID of the user
            db_session: Database session

        Returns:
            List of recommended resources
        """
        from models.transaction import Transaction

        # Find resource types user has used in the past
        past_resources = db_session.query(Resource.type, func.count(Resource.id).label('usage_count')) \
            .join(Transaction, Transaction.resource_id == Resource.id) \
            .filter(Transaction.consumer_id == user_id) \
            .group_by(Resource.type) \
            .order_by(func.count(Resource.id).desc()) \
            .all()

        recommended = []

        # For each previously used resource type, find available similar resources
        for resource_type, _ in past_resources:
            similar_resources = db_session.query(Resource) \
                .filter(Resource.status == 'available',
                        Resource.type == resource_type,
                        Resource.user_id != user_id) \
                .order_by(Resource.credits_per_hour.asc()) \
                .limit(3) \
                .all()

            recommended.extend(similar_resources)

        # If we still need more recommendations, add some popular resources
        if len(recommended) < 5:
            popular_resources = db_session.query(Resource) \
                .join(Transaction, Transaction.resource_id == Resource.id) \
                .filter(Resource.status == 'available',
                        Resource.user_id != user_id) \
                .group_by(Resource.id) \
                .order_by(func.count(Transaction.id).desc()) \
                .limit(5 - len(recommended)) \
                .all()

            recommended.extend(popular_resources)

        return recommended

    @staticmethod
    def calculate_optimal_price(resource_type, capacity, db_session=None):
        """
        Calculate optimal price for a new resource based on market data

        Args:
            resource_type: Type of resource
            capacity: Resource capacity
            db_session: Database session

        Returns:
            Recommended credits per hour
        """
        # Find average price per unit for similar resources
        similar_resources = db_session.query(
            func.avg(Resource.credits_per_hour / Resource.capacity).label('avg_unit_price')
        ).filter(
            Resource.type == resource_type,
            Resource.capacity > 0  # Avoid division by zero
        ).scalar()

        if similar_resources:
            # Calculate price based on market average
            recommended_price = similar_resources * capacity
            # Round to 2 decimal places
            return round(recommended_price, 2)
        else:
            # Default pricing if no market data
            default_prices = {
                'CPU': 2.0 * capacity,
                'GPU': 5.0 * capacity,
                'RAM': 1.0 * capacity,
                'Storage': 0.5 * capacity,
                'Network': 3.0 * capacity
            }
            return default_prices.get(resource_type, 1.0 * capacity)