from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class UserService:
    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """Create a new user ensuring unique email."""
        existing = db.query(User).filter(User.email == user_in.email.lower()).first()
        if existing:
            raise ValueError(f"User with email '{user_in.email}' already exists.")
        
        user = User(
            email=user_in.email.lower(),
            full_name=user_in.full_name,
            role=user_in.role,
            is_active=user_in.is_active
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower()).first()

    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
        update_data = user_in.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"]:
            new_email = update_data["email"].lower()
            if new_email != user.email:
                existing = db.query(User).filter(User.email == new_email).first()
                if existing:
                    raise ValueError(f"Email '{new_email}' is already taken.")
                user.email = new_email

        for field, value in update_data.items():
            if field != "email":
                setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user
