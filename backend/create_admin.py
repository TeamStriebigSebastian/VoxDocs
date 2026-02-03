import asyncio
import sys
import os

# Add current directory to path so imports work
sys.path.append(os.getcwd())

from app.core.database import async_session_maker
from app.models.tenant import Tenant, Group
from app.models.user import User
from app.models.user_role import UserGroupRole, UserRole
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    print("Connecting to database...")
    async with async_session_maker() as session:
        # 1. Create Tenant
        result = await session.execute(select(Tenant).limit(1))
        tenant = result.scalars().first()
        
        if not tenant:
            tenant = Tenant(name="Demo Tenant", settings={})
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            print(f"Created Tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"Using existing Tenant: {tenant.name} (ID: {tenant.id})")

        # 2. Create Group
        result = await session.execute(select(Group).where(Group.tenant_id == tenant.id).limit(1))
        group = result.scalars().first()
        
        if not group:
            group = Group(name="Demo Group", tenant_id=tenant.id)
            session.add(group)
            await session.commit()
            await session.refresh(group)
            print(f"Created Group: {group.name} (ID: {group.id})")
        else:
            print(f"Using existing Group: {group.name} (ID: {group.id})")

        # 3. Create Admin User
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalars().first()
        
        if not user:
            user = User(
                username="admin",
                email="admin@voxdocs.eu",
                password_hash=get_password_hash("admin"),
                tenant_id=tenant.id,
                active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print("Created Admin User: admin")
        else:
            # Update password just in case
            user.password_hash = get_password_hash("admin")
            user.active = True
            await session.commit()
            print("Updated existing Admin User: admin")

        # 4. Assign Role
        result = await session.execute(
            select(UserGroupRole).where(
                UserGroupRole.user_id == user.id,
                UserGroupRole.group_id == group.id
            )
        )
        role = result.scalars().first()
        
        if not role:
            role = UserGroupRole(
                user_id=user.id,
                group_id=group.id,
                role=UserRole.ADMIN,
                can_manage_users=True
            )
            session.add(role)
            await session.commit()
            print(f"Assigned ADMIN role to user {user.username} in group {group.name}")
        else:
            print("User already has role in group")

if __name__ == "__main__":
    asyncio.run(create_admin())
