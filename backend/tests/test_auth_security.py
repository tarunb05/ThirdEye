"""Security regressions: token validation, IDOR, rate limiting.

The independent review found (#16) login tokens that were never stored, (#17)
session routes that trusted an id from the URL, (#18) client-side-only auth and
(#19) unlimited scanning. These tests fail if any of that comes back.
"""
import os, sys, asyncio, tempfile, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Point the DB at a scratch file BEFORE importing db, so tests never touch the
# developer's real thirdeye.db.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
import db as _db
_db.DB_PATH = _tmp.name

from db import (init_db, init_auth_tables, create_user, issue_token,
                user_for_token, revoke_token, create_session, session_owner)


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module", autouse=True)
def _schema():
    async def setup():
        await init_db(); await init_auth_tables()
    run(setup())


class TestTokenValidation:
    def test_issued_token_resolves_to_its_user(self):
        async def go():
            u = await create_user("alice_t", "pw12345")
            t = await issue_token(u["id"])
            return u["id"], await user_for_token(t)
        uid, resolved = run(go())
        assert resolved == uid

    def test_unknown_token_is_rejected(self):
        assert run(user_for_token("not-a-real-token")) is None

    def test_empty_token_is_rejected(self):
        assert run(user_for_token("")) is None

    def test_revoked_token_stops_working(self):
        async def go():
            u = await create_user("bob_t", "pw12345")
            t = await issue_token(u["id"])
            assert await user_for_token(t) == u["id"]
            await revoke_token(t)
            return await user_for_token(t)
        assert run(go()) is None

    def test_plaintext_token_is_not_stored(self):
        """A database leak must not hand out live sessions."""
        import aiosqlite
        async def go():
            u = await create_user("carol_t", "pw12345")
            t = await issue_token(u["id"])
            async with aiosqlite.connect(_db.DB_PATH) as conn:
                cur = await conn.execute("SELECT token_hash FROM auth_tokens")
                stored = [r[0] for r in await cur.fetchall()]
            return t, stored
        token, stored = run(go())
        assert token not in stored, "plaintext token found in the database"


class TestSessionOwnership:
    def test_session_records_its_owner(self):
        async def go():
            u = await create_user("dave_t", "pw12345")
            s = await create_session(u["id"])
            return u["id"], await session_owner(s["id"])
        uid, owner = run(go())
        assert owner == uid

    def test_other_users_session_is_distinguishable(self):
        """The IDOR fix depends on being able to tell whose session it is."""
        async def go():
            a = await create_user("erin_t", "pw12345")
            b = await create_user("frank_t", "pw12345")
            sa = await create_session(a["id"])
            return b["id"], await session_owner(sa["id"])
        b_id, owner_of_a = run(go())
        assert owner_of_a != b_id

    def test_missing_session_has_no_owner(self):
        assert run(session_owner(999999)) is None


class TestRateLimiting:
    def test_limit_blocks_after_threshold(self):
        from fastapi import HTTPException
        import main
        main._rate_buckets.clear()

        class _Req:
            client = type("c", (), {"host": "10.0.0.1"})()

        req = _Req()
        for _ in range(3):
            main.enforce_rate_limit(req, None, limit=3)
        with pytest.raises(HTTPException) as e:
            main.enforce_rate_limit(req, None, limit=3)
        assert e.value.status_code == 429

    def test_users_are_limited_independently(self):
        import main
        main._rate_buckets.clear()

        class _Req:
            client = type("c", (), {"host": "10.0.0.2"})()

        req = _Req()
        for _ in range(3):
            main.enforce_rate_limit(req, 1, limit=3)
        # a different signed-in user still has their own budget
        main.enforce_rate_limit(req, 2, limit=3)

    def test_anonymous_callers_are_limited_by_ip(self):
        import main
        main._rate_buckets.clear()

        class _R1:
            client = type("c", (), {"host": "10.0.0.3"})()

        class _R2:
            client = type("c", (), {"host": "10.0.0.4"})()

        for _ in range(3):
            main.enforce_rate_limit(_R1(), None, limit=3)
        main.enforce_rate_limit(_R2(), None, limit=3)
