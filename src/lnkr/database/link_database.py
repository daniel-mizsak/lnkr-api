"""
Low level database operations for link management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from sqlmodel import Session, col, func, select

from lnkr.models import Link, User


def add_link(session: Session, link: Link) -> Link:
    """Add link to database."""
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def get_link_by_slug(session: Session, slug: str) -> Link | None:
    """Get link from database by slug."""
    return session.exec(select(Link).where(Link.slug == slug).limit(1)).first()


def delete_link(session: Session, link: Link) -> None:
    """Delete link from database."""
    session.delete(link)
    session.commit()


def count_links_by_user(session: Session, user: User) -> int:
    """Count the number of links owned by a user."""
    statement = select(func.count()).where(Link.user_id == user.id)
    return session.exec(statement).one()


def list_links_by_user(session: Session, user: User, per_page: int, page: int) -> list[Link]:
    """List all links owned by a user."""
    offset = (page - 1) * per_page
    statement = select(Link).where(Link.user_id == user.id).order_by(col(Link.id).desc()).offset(offset).limit(per_page)
    return list(session.exec(statement).all())
