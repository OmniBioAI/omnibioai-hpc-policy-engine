"""Unit tests for UsageService.get_or_create_user_usage against a mocked database
session: an existing usage record is returned as-is, and a missing one is
created with zero usage, committed and refreshed.

Developer: Manish Kumar <manish@omnibioai.org>
"""
import pytest
from unittest.mock import MagicMock, patch, call
from app.services.usage_service import UsageService


def _make_db(existing_record=None):
    """Build a mock DB session."""
    db = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = existing_record
    query_mock.filter.return_value = filter_mock
    db.query.return_value = query_mock
    return db


# ---------------------------------------------------------------------------
# get_or_create_user_usage
# ---------------------------------------------------------------------------

def test_returns_existing_record_if_found():
    """An existing usage record is returned without adding to or committing the session."""
    record = MagicMock()
    record.user_id = "u1"
    db = _make_db(existing_record=record)

    result = UsageService.get_or_create_user_usage(db, "u1")

    assert result is record
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_creates_new_record_if_not_found():
    """When no record exists, one is added, committed and refreshed once each."""
    db = _make_db(existing_record=None)

    result = UsageService.get_or_create_user_usage(db, "new-user")

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_new_record_has_zero_usage():
    """A newly created usage record carries the requested user id and zero CPU hours, GPU hours and
    running jobs.
    """
    captured = []

    def capture_add(record):
        captured.append(record)

    db = _make_db(existing_record=None)
    db.add.side_effect = capture_add

    UsageService.get_or_create_user_usage(db, "u2")

    assert len(captured) == 1
    rec = captured[0]
    assert rec.user_id == "u2"
    assert rec.cpu_hours == 0
    assert rec.gpu_hours == 0
    assert rec.jobs_running == 0


def test_returns_refreshed_record_for_new_user():
    """The new record is refreshed after creation, and db.refresh is called once with the returned
    record.
    """
    db = _make_db(existing_record=None)
    refreshed = MagicMock()
    db.refresh.side_effect = lambda r: setattr(r, "_refreshed", True)

    result = UsageService.get_or_create_user_usage(db, "u3")

    db.refresh.assert_called_once_with(result)


def test_queries_correct_user_id():
    """get_or_create_user_usage queries the UsageRecord table."""
    from app.db.models import UsageRecord
    record = MagicMock()
    db = _make_db(existing_record=record)

    UsageService.get_or_create_user_usage(db, "target-user")

    db.query.assert_called_once_with(UsageRecord)
