from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    try:
        return UserService.create_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve all users."""
    return UserService.list_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Retrieve a user by ID."""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's details."""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        return UserService.update_user(db, user, user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
