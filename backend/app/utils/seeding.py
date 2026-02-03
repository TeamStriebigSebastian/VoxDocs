from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.models.tenant import Tenant, Group
from app.models.user import User
from app.models.user_role import UserRole, UserGroupRole
from app.core.auth import get_password_hash

async def seed_default_platform_data(db: AsyncSession):
    """
    Seed the database with default Tenant, Group, and User.
    Required for the generic platform frontend.
    """
    try:
        logger.info("Starting platform data seeding...")
        
        # 1. Seed Tenant
        result = await db.execute(select(Tenant).where(Tenant.id == 1))
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.info("Creating default Tenant (ID=1)...")
            tenant = Tenant(
                id=1,
                name="Default Tenant",
                settings={"locale": "de-DE"},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tenant)
            await db.flush()
        
        # 2. Seed Group
        result = await db.execute(select(Group).where(Group.id == 1))
        group = result.scalar_one_or_none()
        if not group:
            logger.info("Creating default Group (ID=1)...")
            group = Group(
                id=1,
                tenant_id=1,
                name="Generic Case Management",
                created_at=datetime.utcnow()
            )
            db.add(group)
            await db.flush()

        # 3. Seed User with proper password hash
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        if not user:
            logger.info("Creating default admin User (ID=1)...")
            # Default password: admin123 (change in production!)
            user = User(
                id=1,
                tenant_id=1,
                username="admin",
                email="admin@voxdocs.local",
                password_hash=get_password_hash("admin123"),
                active=True,
                created_at=datetime.utcnow()
            )
            db.add(user)
            await db.flush()
            
            # 4. Assign ADMIN role to user for group
            logger.info("Assigning ADMIN role to user for group 1...")
            user_role = UserGroupRole(
                user_id=1,
                group_id=1,
                role=UserRole.ADMIN,
                can_manage_users=True
            )
            db.add(user_role)
            await db.flush()

        await db.commit()
        logger.info("Platform seeding completed successfully.")

    except Exception as e:
        logger.error(f"Error seeding platform data: {e}")
        await db.rollback()
        raise

