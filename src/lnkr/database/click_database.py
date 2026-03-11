"""
Low level database operations for click management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from lnkr.models import Click, Link

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def add_click(session: Session, click: Click) -> Click:
    """Add click to database."""
    session.add(click)
    session.commit()
    session.refresh(click)
    return click


def list_clicks_by_link(session: Session, link: Link, per_page: int, page: int) -> list[Click]:
    """List all clicks for a link."""
    offset = (page - 1) * per_page
    statement = (
        select(Click).where(Click.link_id == link.id).order_by(Click.timestamp.desc()).offset(offset).limit(per_page)
    )
    result = session.execute(statement)
    return list(result.scalars().all())
