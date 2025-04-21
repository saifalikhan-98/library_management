import traceback

import bcrypt
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role

from app.config import settings

logger = logging.getLogger(__name__)


async def create_admin_user():
    db = SessionLocal()
    try:

        roles = {
            "user": {"description": "Regular library user with basic permissions", "access_level": 1},
            "librarian": {"description": "Library staff with advanced book management permissions", "access_level": 2},
            "admin": {"description": "Administrator with full system access", "access_level": 3}
        }

        # Create roles if they don't exist
        for role_name, meta in roles.items():
            role = db.query(Role).filter(Role.role_name == role_name).first()
            if not role:
                logger.info(f"Creating role {role_name}")
                new_role = Role(role_name=role_name, description=meta["description"],
                                access_level=meta["access_level"])
                db.add(new_role)
                db.commit()
            else:
                logger.info(f"Role {role_name} already present")

        # Check if admin user exists
        admin_username = settings.ADMIN_USERNAME
        admin_user = db.query(User).filter(User.username == admin_username).first()

        if not admin_user:
            #1 stands for admin access role
            admin_role = db.query(Role).filter(Role.access_level == 1).first()

            if not admin_role:
                logger.error("Admin role not found. Cannot create admin user.")
                return

            logger.info(f"Creating Admin user")
            password=settings.ADMIN_INITIAL_PASSWORD
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt()
            hash = bcrypt.hashpw(password_bytes, salt)
            hashed_pwd=hash.decode('utf-8')
            admin_user = User(
                username=admin_username,
                email=settings.ADMIN_EMAIL,
                password=hashed_pwd,
                first_name="System",
                last_name="Administrator",
                is_active=True,
                role_id=admin_role.role_id
            )

            db.add(admin_user)
            db.commit()

        else:
            logger.info("Admin already present")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error: {str(e)}")
        traceback.print_exc()
        db.rollback()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        traceback.print_exc()
    finally:
        db.close()