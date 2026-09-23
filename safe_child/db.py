"""Thin Supabase wrapper for Safe Child (production).

Pure Python — no reflex dependency, safe to import anywhere.
All functions take/return plain dicts.

The database is OPTIONAL: any network failure raises
``RuntimeError("database unavailable")`` so the app can fall back to
offline/demo mode. Missing credentials raise RuntimeError with a clear
message instead.
"""

from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def _get_create_client() -> Callable[..., Any]:
    """Import supabase-py lazily so this module stays import-safe."""
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "supabase package is not installed; run: pip install supabase"
        ) from exc
    return create_client


def get_client() -> Any:
    """Return an authenticated Supabase client.

    Reads SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_KEY) from the
    environment. Raises RuntimeError with a clear message if either is missing.
    """
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        or os.environ.get("SUPABASE_KEY", "").strip()
    )
    if not url:
        raise RuntimeError(
            "SUPABASE_URL is not set; set it in the environment to enable the database"
        )
    if not key:
        raise RuntimeError(
            "SUPABASE_KEY (or SUPABASE_SERVICE_KEY) is not set; "
            "set it in the environment to enable the database"
        )
    return _get_create_client()(url, key)


def _db_call(fn: Callable[[], T]) -> T:
    """Run a DB call, mapping network/driver failures to RuntimeError.

    RuntimeError (missing credentials) and ValueError("exists") (duplicate
    identity) pass through unchanged.
    """
    try:
        return fn()
    except (RuntimeError, ValueError):
        raise
    except Exception as exc:
        raise RuntimeError("database unavailable") from exc


def find_user(identity: str) -> dict | None:
    """Find a user by phone or email, matched case-insensitively.

    Returns the user row as a dict, or None if not found.
    """
    client = get_client()

    def _q() -> dict | None:
        res = (
            client.table("users")
            .select("*")
            .ilike("identity", identity)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return dict(rows[0]) if rows else None

    return _db_call(_q)


def create_user(name: str, identity: str, pw_hash: str) -> dict:
    """Insert a new user. Raises ValueError("exists") if identity is taken."""
    client = get_client()

    def _q() -> dict:
        existing = (
            client.table("users")
            .select("id")
            .ilike("identity", identity)
            .limit(1)
            .execute()
        )
        if existing.data:
            raise ValueError("exists")
        res = (
            client.table("users")
            .insert({"name": name, "identity": identity, "pw_hash": pw_hash})
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise RuntimeError("database unavailable")
        return dict(rows[0])

    return _db_call(_q)


def save_screening(user_id: str | None, payload: dict) -> dict:
    """Save a screening result. Returns the inserted row (with id)."""
    client = get_client()

    def _q() -> dict:
        res = (
            client.table("screenings")
            .insert(
                {
                    "user_id": user_id,
                    "age_group": payload.get("age_group"),
                    "answers": payload.get("answers", {}),
                    "score": payload.get("score"),
                    "band": payload.get("band"),
                    "critical": bool(payload.get("critical", False)),
                }
            )
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise RuntimeError("database unavailable")
        return dict(rows[0])

    return _db_call(_q)


def save_report(user_id: str | None, case_id: str, payload: dict) -> dict:
    """Save a filed report. Returns the inserted row (with id)."""
    client = get_client()

    def _q() -> dict:
        res = (
            client.table("reports")
            .insert(
                {
                    "user_id": user_id,
                    "case_id": case_id,
                    "data": payload,
                    "status": payload.get("status", "draft"),
                }
            )
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise RuntimeError("database unavailable")
        return dict(rows[0])

    return _db_call(_q)


def list_reports(user_id: str) -> list[dict]:
    """List a user's reports, newest first."""
    client = get_client()

    def _q() -> list[dict]:
        res = (
            client.table("reports")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [dict(r) for r in (res.data or [])]

    return _db_call(_q)


def update_report_status(case_id: str, status: str) -> None:
    """Update a report's status by its case id."""
    client = get_client()

    def _q() -> None:
        client.table("reports").update({"status": status}).eq(
            "case_id", case_id
        ).execute()

    _db_call(_q)
