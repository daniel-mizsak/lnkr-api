"""
High level database operations for click management.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

from typing import TYPE_CHECKING

from lnkr.database import click_database
from lnkr.models import Click, ClickCreate, Link

if TYPE_CHECKING:
    import uuid

    from sqlmodel import Session


def create_click(session: Session, click_create: ClickCreate, link_id: uuid.UUID) -> Click:
    """Create a click in the database.

    Args:
        session (Session): The database session.
        click_create (ClickCreate): The data model for creating a click.
        link_id (uuid.UUID): The id of the link the click belongs to.

    Returns:
        Click: Click object.
    """
    return click_database.add_click(session, Click.from_click_create(click_create, link_id))


def list_clicks(session: Session, link: Link, per_page: int, page: int) -> list[Click]:
    """List all clicks for a given link.

    Args:
        session (Session): The database session.
        link (Link): The link to list clicks for.
        per_page (int): The number of clicks to return per page. Maximum is 100.
        page (int): The page number of the clicks to return.

    Returns:
        list[Click]: A list of click objects.
    """
    per_page = min(per_page, 100)
    return click_database.list_clicks_by_link(session, link, per_page, page)
