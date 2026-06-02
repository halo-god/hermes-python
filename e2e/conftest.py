import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"
ADMIN_EMAIL = "admin@hermes.io"
ADMIN_PASSWORD="Herm...@2026"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "base_url": BASE_URL}


@pytest.fixture
def logged_in_page(page: Page):
    """Login as admin and return page."""
    login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    return page


def login(page: Page, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD):
    """Perform login flow."""
    page.goto("/login")
    page.fill('input[type="text"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("/")
