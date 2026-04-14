"""Tests for SPMS Flask application routes."""

import pytest


class TestPublicRoutes:
    """Test public routes (no authentication required)."""
    
    def test_index_page_loads(self, client):
        """Test that index page loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'SPMS' in response.data
    
    def test_login_page_loads(self, client):
        """Test that login page loads."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data.decode('utf-8').lower()
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'status' in data
        assert 'database' in data


class TestAuthenticationRoutes:
    """Test authentication protected routes."""
    
    def test_student_dashboard_requires_login(self, client):
        """Test that student dashboard requires login."""
        response = client.get('/student/dashboard')
        assert response.status_code == 302  # Redirect to login
        assert '/login' in response.location
    
    def test_teacher_dashboard_requires_login(self, client):
        """Test that teacher dashboard requires login."""
        response = client.get('/teacher/dashboard')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_admin_dashboard_requires_login(self, client):
        """Test that admin dashboard requires login."""
        response = client.get('/admin/dashboard')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_logout_clears_session(self, client):
        """Test that logout clears user session."""
        with client:
            client.get('/logout')
            # Session should be cleared
            response = client.get('/student/dashboard')
            assert response.status_code == 302


class TestAPIEndpoints:
    """Test REST API endpoints."""
    
    def test_api_endpoints_require_login(self, client):
        """Test that API endpoints require authentication."""
        endpoints = [
            '/api/teacher/subjects',
            '/api/student-results/test',
            '/api/admin/statistics',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 302 or response.status_code == 403
