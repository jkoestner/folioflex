"""Dashboard login handler."""

import dash

restricted_page = {}


def require_login(page):
    """Require login for a page."""
    for pg in dash.page_registry:
        if page == pg:
            restricted_page[dash.page_registry[pg]["path"]] = True
