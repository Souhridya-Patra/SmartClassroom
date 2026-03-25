import sys
import os
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app, get_connection

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Backend running"}

def test_register_student():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    def get_mock_db():
        yield mock_conn

    app.dependency_overrides[get_connection] = get_mock_db

    student_data = {"id": "123", "name": "test", "email": "test@test.com"}
    response = client.post("/register-student", json=student_data, headers={"X-API-Key": "mysecretkey"})

    assert response.status_code == 200
    assert response.json() == student_data
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()

    # Clean up
    app.dependency_overrides = {}

def test_start_session():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.lastrowid = 1

    def get_mock_db():
        yield mock_conn

    app.dependency_overrides[get_connection] = get_mock_db

    session_data = {"professor_id": 1}
    response = client.post("/start-session", json=session_data, headers={"X-API-Key": "mysecretkey"})

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["professor_id"] == 1
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()

    # Clean up
    app.dependency_overrides = {}

def test_stop_session():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {"id": 1, "professor_id": 1, "start_time": "2024-01-01T00:00:00", "end_time": "2024-01-01T01:00:00"}

    def get_mock_db():
        yield mock_conn

    app.dependency_overrides[get_connection] = get_mock_db

    response = client.post("/stop-session/1", headers={"X-API-Key": "mysecretkey"})

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["end_time"] is not None
    assert mock_cursor.execute.call_count == 2
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()

    # Clean up
    app.dependency_overrides = {}

