"""
Resource allocation algorithms for the Decentralized Cloud Resource Gateway
"""
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from models.resource import Resource
from models.user import User


class ResourceAllocator:
    """
    Handles resource allocation strategies for matching users with resources
    """

    @staticmethod
    def find_best_match(user_id, resource_type, capacity_needed, max_credits=None, db_session=None):
        """
        Find the best available resource match based on user requirements

        Args:
            user_id: The ID of the user requesting resources
            resource_type: Type of resource needed (CPU, GPU, etc)
            capacity_needed: Minimum capacity required
            max_credits: Maximum credits user is willing to spend per hour
            db_session: Database session

        Returns:
            A list of matching resources
        """
        query = db_session.query(Resource).filter(
            Resource.status == 'available',
            Resource.type == resource_type,
            Resource.capacity >= capacity_needed,
            Resource.user_id != user_id  # Don't match user's own resources
        )

        if max_credits:
            query = query.filter(Resource.credits_per_hour <= max_credits)

        # Sort by best value (credits per capacity unit)
        query = query.order_by((Resource.credits_per_hour / Resource.capacity).asc())

        return query.all()

    @staticmethod
    def allocate_resource(resource_id, user_id, hours, db_session=None):
        """
        Allocate a resource to a user

        Args:
            resource_id: ID of the resource to allocate
            user_id: ID of the user borrowing the resource
            hours: Number of hours to borrow the resource
            db_session: Database session

        Returns:
            (success, message, transaction_id)
        """
        from models.transaction import Transaction

        resource = db_session.query(Resource).get(resource_id)
        user = db_session.query(User).get(user_id)

        if not resource or not user:
            return False, "Resource or user not found", None

        if resource.status != 'available':
            return False, "Resource is not available", None

        total_cost = resource.credits_per_hour * hours

        if user.credits < total_cost:
            return False, "Insufficient credits", None

        # Create transaction
        transaction = Transaction(
            resource_id=resource_id,
            provider_id=resource.user_id,
            consumer_id=user_id,
            credits=total_cost,
            # Set end time based on hours
            end_time=datetime.utcnow() + timedelta(hours=hours)
        )

        # Update resource status
        resource.status = 'in_use'
        resource.borrowed_by = user_id

        # Update user credits
        user.credits -= total_cost
        provider = db_session.query(User).get(resource.user_id)
        provider.credits += total_cost

        db_session.add(transaction)
        db_session.commit()

        return True, "Resource allocated successfully", transaction.id

    @staticmethod
    def release_resource(resource_id, user_id, db_session=None):
        """
        Release a borrowed resource

        Args:
            resource_id: ID of the resource to release
            user_id: ID of the user releasing the resource
            db_session: Database session

        Returns:
            (success, message)
        """
        from models.transaction import Transaction

        resource = db_session.query(Resource).get(resource_id)

        if not resource:
            return False, "Resource not found"

        if resource.borrowed_by != user_id:
            return False, "You cannot release this resource"

        # Find active transaction
        transaction = db_session.query(Transaction).filter(
            Transaction.resource_id == resource_id,
            Transaction.consumer_id == user_id,
            Transaction.status == 'active'
        ).first()

        if transaction:
            transaction.status = 'completed'
            transaction.end_time = datetime.utcnow()

        # Reset resource status
        resource.status = 'available'
        resource.borrowed_by = None

        db_session.commit()

        return True, "Resource released successfully"