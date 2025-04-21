from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User
from app.models.api_key import UserApiKey


class UserApiKeyService:

    def create_api_key_mapping(self, user:User, db:Session)->str:
       raw_api_key=UserApiKey.generate_api_key()
       hashed_key=UserApiKey.hash_key(api_key=raw_api_key)

       expires_at = datetime.utcnow() + timedelta(days=90)
       api_key=UserApiKey(
           user_id=user.user_id,
           key_hash=hashed_key,
           expires_at=expires_at
       )
       db.add(api_key)
       db.commit()
       db.refresh(api_key)

       return raw_api_key

    def validate_api_key(self, api_key: str, db:Session, user_id:int) ->tuple[bool, str, UserApiKey|None]:
        now = datetime.utcnow()
        active_key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user_id,
            UserApiKey.is_active == True,

        ).first()
        if active_key is None:
            return False, "Api key not found",None

        if active_key.expires_at < now:
            return False, "Api key has been expired, Please generate a new one",None

        verify_key=UserApiKey.verify_key(api_key, active_key.key_hash)

        if not verify_key:
            return False, "Invalid credentials, Please put correct api key",None

        return True, "Credentials verified",active_key



    def reset_api_key(self, user:User, db:Session)->str:
        raw_api_key = UserApiKey.generate_api_key()
        hashed_key = UserApiKey.hash_key(api_key=raw_api_key)

        # Set expiration date (90 days from now)
        expires_at = datetime.utcnow() + timedelta(days=90)

        # Find existing key for this user
        existing_key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user.user_id
        ).first()

        if existing_key:
            # Update existing key
            existing_key.key_hash = hashed_key
            existing_key.expires_at = expires_at
            existing_key.is_active = True
            existing_key.last_used_at = None  # Reset last_used_at
        else:
            # Create new key if none exists
            api_key = UserApiKey(
                user_id=user.user_id,
                key_hash=hashed_key,
                expires_at=expires_at
            )
            db.add(api_key)

        db.commit()

        return raw_api_key
