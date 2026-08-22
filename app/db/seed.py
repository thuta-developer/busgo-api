import argparse
import asyncio
import getpass
import logging
import sys
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.rbac import Permission, Role
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# 1. DYNAMIC PERMISSIONS DEFINITIONS
# ==========================================
CRUD_ACTIONS = ["create", "read", "update", "delete"]
CRUD_RESOURCES = [
    "user",
    "role",
    "permission",
    "bus",
    "bus_company",
    "route",
    "trip",
    "booking",
    "payment",
    "promotion",
]

# Admin-scoped permissions (not part of standard CRUD but used by admin APIs)
ADMIN_PERMISSIONS = [
    {
        "name": "booking:read_admin",
        "description": "Can view all booking list and trip bookings (Admin)",
        "module": "Booking",
    },
    {
        "name": "booking:update_admin",
        "description": "Can update booking status and cleanup expired bookings (Admin)",
        "module": "Booking",
    },
]


def build_permissions() -> List[Dict[str, str]]:
    """Generate resource permission pairs dynamically."""
    perms = []
    for resource in CRUD_RESOURCES:
        for action in CRUD_ACTIONS:
            perms.append({
                "name": f"{resource}:{action}",
                "description": f"Can {action} {resource}",
                "module": resource.capitalize(),
            })
    # Append admin-scoped permissions
    perms.extend(ADMIN_PERMISSIONS)
    return perms


PERMISSIONS = build_permissions()

# ==========================================
# 2. DEFAULT ROLES SETUP
# ==========================================
DEFAULT_ROLES = {
    "Super Admin": {
        "description": "Full access to all modules and configurations",
        "permissions": "*",  # All permissions
    },
}


# ==========================================
# 3. RBAC SEEDING LOGIC
# ==========================================
async def seed_rbac(sync_stale_roles: bool = False):
    """Seed permissions and roles using pure async ORM."""
    logger.info("🌱 Seeding RBAC Data (Permissions & Roles)...")

    async with AsyncSessionLocal() as session:
        # A. Seed Permissions (Bulk Fetch)
        existing_perms_res = await session.execute(select(Permission))
        existing_perms = {p.name: p for p in existing_perms_res.scalars().all()}

        perm_objects: Dict[str, Permission] = {}
        for perm_data in PERMISSIONS:
            name = perm_data["name"]
            if name in existing_perms:
                perm_objects[name] = existing_perms[name]
            else:
                new_perm = Permission(**perm_data)
                session.add(new_perm)
                perm_objects[name] = new_perm

        await session.flush()
        logger.info(f"   [+] Synced {len(PERMISSIONS)} permissions.")

        # B. Sync Stale Roles (Optional Clean-up using Pure ORM)
        if sync_stale_roles:
            active_role_names = list(DEFAULT_ROLES.keys())
            stale_roles_res = await session.execute(
                select(Role).options(selectinload(Role.permissions)).where(Role.name.not_in(active_role_names))
            )
            stale_roles = stale_roles_res.scalars().all()

            if stale_roles:
                for stale_role in stale_roles:
                    stale_role.permissions = []  # Clear Join Table links cleanly
                    await session.delete(stale_role)
                
                stale_names = [r.name for r in stale_roles]
                logger.info(f"   🧹 Cleaned stale roles: {', '.join(stale_names)}")

        # C. Seed / Update Roles
        existing_roles_res = await session.execute(
            select(Role).options(selectinload(Role.permissions))
        )
        existing_roles = {r.name: r for r in existing_roles_res.scalars().all()}

        for role_name, config in DEFAULT_ROLES.items():
            if config["permissions"] == "*":
                target_perms = list(perm_objects.values())
            else:
                target_perms = [
                    perm_objects[p] for p in config["permissions"] if p in perm_objects
                ]

            if role_name in existing_roles:
                role = existing_roles[role_name]
                role.description = config["description"]
            else:
                role = Role(name=role_name, description=config["description"])
                session.add(role)

            role.permissions = target_perms

        await session.commit()
        logger.info("✅ RBAC Seeding Complete!")


# ==========================================
# 4. DYNAMIC SUPER ADMIN CREATION LOGIC
# ==========================================
async def create_super_admin(
    email: str,
    password: str,
    full_name: str = "Super Admin",
    phone_number: Optional[str] = None,
):
    """Create or promote a user to Super Admin dynamically."""
    logger.info(f"👤 Creating Super Admin for email: {email}...")

    async with AsyncSessionLocal() as session:
        # Check Super Admin Role
        role_res = await session.execute(
            select(Role).where(Role.name == "Super Admin")
        )
        super_admin_role = role_res.scalar_one_or_none()

        if not super_admin_role:
            logger.error("❌ 'Super Admin' role not found! Run 'python -m app.db.seed rbac' first.")
            return

        # Check existing user
        user_res = await session.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        user = user_res.scalar_one_or_none()

        if user:
            logger.info(f"   [*] User '{email}' already exists. Promoting to Super Admin...")
            user.is_superuser = True
            user.is_active = True
            if super_admin_role not in user.roles:
                user.roles.append(super_admin_role)
        else:
            user = User(
                full_name=full_name,
                email=email,
                phone_number=phone_number or "09000000000",
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=True,
                is_verified=True,
                roles=[super_admin_role],
            )
            session.add(user)

        await session.commit()
        logger.info(f"✅ Super Admin '{email}' created/updated successfully!")


# ==========================================
# 5. CLI ARGUMENT PARSER
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="BusGo API Seeder CLI Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # Command: rbac
    rbac_parser = subparsers.add_parser("rbac", help="Seed Permissions and Default Roles")
    rbac_parser.add_argument(
        "--sync", action="store_true", help="Delete stale roles not defined in code"
    )

    # Command: create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Create a Super Admin user dynamically")
    admin_parser.add_argument("--email", type=str, help="Admin Email address")
    admin_parser.add_argument("--password", type=str, help="Admin Password")
    admin_parser.add_argument("--name", type=str, default="System Super Admin", help="Full Name")
    admin_parser.add_argument("--phone", type=str, default=None, help="Phone Number")

    args = parser.parse_args()

    if args.command == "rbac":
        asyncio.run(seed_rbac(sync_stale_roles=args.sync))

    elif args.command == "create-admin":
        email = args.email or input("Enter Super Admin Email: ").strip()
        
        if not args.password:
            password = getpass.getpass("Enter Super Admin Password: ").strip()
            confirm_password = getpass.getpass("Confirm Password: ").strip()
            if password != confirm_password:
                logger.error("❌ Passwords do not match!")
                sys.exit(1)
        else:
            password = args.password

        if not email or not password:
            logger.error("❌ Email and Password are required!")
            sys.exit(1)

        asyncio.run(create_super_admin(
            email=email,
            password=password,
            full_name=args.name,
            phone_number=args.phone
        ))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()