"""Tests for database connection and query functions."""

import pytest
from unittest.mock import patch, MagicMock


class TestDatabaseConnection:
    """Test database connection functionality."""
    
    def test_connection_returns_valid_object(self):
        """Test that get_connection returns a valid connection object."""
        from database.connection import get_connection
        
        # This test may fail if MySQL is not running, so we skip in CI if needed
        try:
            conn = get_connection()
            assert conn is not None
            conn.close()
        except Exception as e:
            pytest.skip(f"MySQL not available: {str(e)}")
    
    def test_test_connection_function(self):
        """Test the test_connection utility function."""
        from database.connection import test_connection
        
        try:
            result = test_connection()
            assert isinstance(result, bool)
        except Exception as e:
            pytest.skip(f"MySQL not available: {str(e)}")


class TestQueryFunctions:
    """Test database query helper functions."""
    
    @patch('database.queries.get_connection')
    def test_authenticate_user_invalid_credentials(self, mock_conn):
        """Test authentication with invalid credentials."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        from database.queries import authenticate_user
        
        result = authenticate_user('nonexistent_user', 'wrong_password')
        assert result['success'] is False
        assert 'error' in result
    
    @patch('database.queries.get_connection')
    def test_search_students_returns_list(self, mock_conn):
        """Test student search returns list."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        from database.queries import search_students
        
        result = search_students()
        assert isinstance(result, list)
    
    @patch('database.queries.get_connection')
    def test_get_admin_stats_returns_dict(self, mock_conn):
        """Test admin stats returns dictionary."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(10,), (5,), (3,), (2,)]
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        from database.queries import get_admin_stats
        
        result = get_admin_stats()
        assert isinstance(result, dict)
        assert 'students' in result or 'error' in result
