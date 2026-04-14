"""Pytest configuration and fixtures for SPMS tests."""

import pytest
import os
from app import create_app


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    # Ensure test database configuration
    os.environ['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
    os.environ['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
    os.environ['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'test_root_password')
    os.environ['MYSQL_DB'] = os.getenv('MYSQL_DB', 'spms_test_db')
    os.environ['MYSQL_PORT'] = os.getenv('MYSQL_PORT', '3306')
    os.environ['SECRET_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config['TESTING'] = True
    
    return app


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner for testing CLI commands."""
    return app.test_cli_runner()
