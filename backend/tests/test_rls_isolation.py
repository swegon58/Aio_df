"""Adversarial DB-layer isolation test for Postgres RLS (checklist item 6 of
``AIO_DF_AUTH_INFRA_PLAN.md``).

Everything else in this repo's test suite runs against SQLite, where RLS
doesn't exist and ``apply_rls_context``/``apply_rls_policies`` are no-ops --
so none of it can catch a broken policy. This test is the one place that
proves the DB itself, not just the app-level ``user_id`` WHERE-clause filter,
refuses cross-user rows: it queries ``threads_meta`` with **no WHERE clause
at all** (the exact mistake RLS is meant to survive) and asserts the session
variable set by ``apply_rls_context`` is what limits the result, not the
query.

Skipped unless ``AIO_DF_TEST_POSTGRES_URL`` is set to a scratch Postgres
database (never SQLite/prod) -- there is no Postgres in the default dev/CI
path, so this can't run unconditionally like the rest of the suite.

**The connecting role must NOT be a superuser or have ``BYPASSRLS``.**
Postgres superusers bypass RLS unconditionally, ``FORCE ROW LEVEL SECURITY``
included -- so pointing this at e.g. a default ``postgres`` superuser role on
a throwaway Docker container makes ``test_rls_blocks_cross_user_rows_...``
fail loudly (safe, not a false pass) rather than actually testing anything.
Create a plain role first, e.g.::

    CREATE ROLE aiodf_app LOGIN PASSWORD '...' NOSUPERUSER NOBYPASSRLS;
    CREATE DATABASE aiodf_rls_test OWNER aiodf_app;
    ALTER SCHEMA public OWNER TO aiodf_app;  -- template db's public schema isn't owned by the new role by default

Supabase's own default ``postgres`` role is not a superuser and has no
``BYPASSRLS`` (unlike a self-hosted Postgres superuser), so production
should behave like this test once pointed at a real Supabase project --
worth a one-time confirmation query (``SELECT rolsuper, rolbypassrls FROM
pg_roles WHERE rolname = current_user``) against the real connection once
step 1 of the plan is done, since a managed-Postgres provider getting this
wrong would silently defeat every policy in ``0004_rls_policies``.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from deerflow.persistence.bootstrap import bootstrap_schema
from deerflow.persistence.rls import apply_rls_context

POSTGRES_URL = os.environ.get("AIO_DF_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="set AIO_DF_TEST_POSTGRES_URL to a scratch Postgres DB to run RLS isolation tests",
)


@pytest_asyncio.fixture
async def pg_session_factory():
    engine = create_async_engine(POSTGRES_URL, pool_size=2)
    await bootstrap_schema(engine, backend="postgres")
    from sqlalchemy.ext.asyncio import async_sessionmaker

    sf = async_sessionmaker(engine, expire_on_commit=False)
    yield sf
    async with engine.begin() as conn:
        await conn.execute(text("SELECT set_config('app.rls_bypass', 'on', false)"))
        await conn.execute(text("DELETE FROM threads_meta WHERE thread_id LIKE 'rls-test-%'"))
    await engine.dispose()


async def _insert_thread(sf, thread_id: str, user_id: str) -> None:
    async with sf() as session:
        await apply_rls_context(session, None)  # bypass=on: insert as system/admin
        now = datetime.now(UTC)
        await session.execute(
            text(
                "INSERT INTO threads_meta (thread_id, user_id, status, metadata_json, created_at, updated_at) "
                "VALUES (:tid, :uid, 'active', '{}', :now, :now)"
            ),
            {"tid": thread_id, "uid": user_id, "now": now},
        )
        await session.commit()


@pytest.mark.asyncio
async def test_rls_blocks_cross_user_rows_even_without_where_clause(pg_session_factory):
    user_a, user_b = f"rls-test-user-a-{uuid.uuid4().hex[:8]}", f"rls-test-user-b-{uuid.uuid4().hex[:8]}"
    thread_a, thread_b = f"rls-test-thread-a-{uuid.uuid4().hex[:8]}", f"rls-test-thread-b-{uuid.uuid4().hex[:8]}"
    await _insert_thread(pg_session_factory, thread_a, user_a)
    await _insert_thread(pg_session_factory, thread_b, user_b)

    async with pg_session_factory() as session:
        await apply_rls_context(session, user_a)
        # Deliberately no "WHERE user_id = ..." -- this is the mistake RLS
        # must survive on its own.
        rows = (await session.execute(text("SELECT thread_id, user_id FROM threads_meta WHERE thread_id LIKE 'rls-test-%'"))).all()

    seen = {r.thread_id: r.user_id for r in rows}
    assert thread_a in seen
    assert thread_b not in seen


@pytest.mark.asyncio
async def test_rls_bypass_flag_sees_all_users(pg_session_factory):
    user_a, user_b = f"rls-test-user-a-{uuid.uuid4().hex[:8]}", f"rls-test-user-b-{uuid.uuid4().hex[:8]}"
    thread_a, thread_b = f"rls-test-thread-a-{uuid.uuid4().hex[:8]}", f"rls-test-thread-b-{uuid.uuid4().hex[:8]}"
    await _insert_thread(pg_session_factory, thread_a, user_a)
    await _insert_thread(pg_session_factory, thread_b, user_b)

    async with pg_session_factory() as session:
        await apply_rls_context(session, None)  # bypass=on, mirrors resolve_user_id's explicit-None state
        rows = (await session.execute(text("SELECT thread_id FROM threads_meta WHERE thread_id LIKE 'rls-test-%'"))).all()

    seen = {r.thread_id for r in rows}
    assert thread_a in seen
    assert thread_b in seen
