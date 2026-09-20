from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate

class CommentService:
    @staticmethod
    def create_comment(db: Session, task_id: int, comment_in: CommentCreate) -> Comment:
        # Verify task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task with id {task_id} does not exist.")

        # Verify author exists
        author = db.query(User).filter(User.id == comment_in.author_id).first()
        if not author:
            raise ValueError(f"Author with id {comment_in.author_id} does not exist.")

        comment = Comment(
            content=comment_in.content,
            task_id=task_id,
            author_id=comment_in.author_id
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def list_comments_for_task(db: Session, task_id: int) -> List[Comment]:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task with id {task_id} does not exist.")
        return (
            db.query(Comment)
            .filter(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc())
            .all()
        )
