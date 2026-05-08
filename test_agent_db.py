"""
Test suite for the three agent DB functions:
  - get_eligible_jobs()
  - mark_agent_applied()
  - mark_agent_failed()

Run from the project root:
    python test_agent_db.py

What this script does:
  1. Inserts a small set of controlled test jobs directly into the DB
  2. Runs each test case, checking every relevant field after each call
  3. Cleans up every test row it inserted, leaving your real data untouched
  4. Prints a PASS / FAIL summary for each test
"""

import os
import sys
from datetime import datetime, timezone

# Make sure lib/ is importable when run from project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from lib.db import (
    Job,
    SessionLocal,
    get_eligible_jobs,
    mark_agent_applied,
    mark_agent_failed,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

# Unique prefix so we can identify and clean up test rows safely
TEST_URL_PREFIX = "https://test.example.com/jobs/agent-db-test/"

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"

results: list[tuple[str, bool, str]] = []  # (test_name, passed, detail)


def check(test_name: str, condition: bool, detail: str = ""):
    """Record and immediately print a single assertion."""
    status = PASS if condition else FAIL
    print(f"  [{status}] {test_name}" + (f" — {detail}" if detail else ""))
    results.append((test_name, condition, detail))


def fetch_job(session, job_id: int) -> Job | None:
    """Re-fetch a job from the DB to verify what was actually committed."""
    return session.query(Job).filter(Job.id == job_id).first()


# ── Fixtures ───────────────────────────────────────────────────────────────────


def insert_test_jobs() -> dict[str, int]:
    """
    Insert a controlled set of test jobs and return a mapping of
    label → job_id so tests can reference them by name.
    """
    session = SessionLocal()
    inserted: dict[str, int] = {}
    try:
        fixtures = [
            # label              status          score  retry_count  applied_at
            ("eligible_high", "New", 9.5, 0, None),
            ("eligible_low", "New", 7.0, 0, None),
            ("eligible_retry1", "New", 8.0, 1, None),
            ("eligible_retry2", "New", 8.0, 2, None),
            ("ineligible_maxed", "New", 8.0, 3, None),  # retry_count = 3 → excluded
            ("ineligible_saved", "Saved", 8.0, 0, None),  # wrong status → excluded
            (
                "applied_preset",
                "New",
                8.5,
                0,
                datetime(2025, 1, 15, 10, 0, 0),
            ),  # has existing applied_at
        ]

        for label, status, score, retry_count, applied_at in fixtures:
            job = Job(
                title=f"Test Job [{label}]",
                company="Test Co",
                url=f"{TEST_URL_PREFIX}{label}",
                score=score,
                status=status,
                retry_count=retry_count,
                applied_at=applied_at,
                scored_on="full_jd",
                reasons="Test fixture",
                auto_apply_ready=True,
            )
            session.add(job)
            session.flush()  # assigns the id without committing
            inserted[label] = job.id

        session.commit()
        print(f"\n  Inserted {len(inserted)} test fixtures: {list(inserted.keys())}")
        return inserted

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to insert test fixtures: {e}") from e
    finally:
        session.close()


def cleanup_test_jobs():
    """Delete every row whose URL starts with the test prefix."""
    session = SessionLocal()
    try:
        deleted = (
            session.query(Job)
            .filter(Job.url.like(f"{TEST_URL_PREFIX}%"))
            .delete(synchronize_session=False)
        )
        session.commit()
        print(f"\n  Cleaned up {deleted} test rows.")
    except Exception as e:
        session.rollback()
        print(f"\n  Cleanup failed: {e}")
    finally:
        session.close()


# ── Test cases ─────────────────────────────────────────────────────────────────


def test_get_eligible_jobs(ids: dict[str, int]):
    print("\n── test_get_eligible_jobs ──────────────────────────────────────")

    jobs = get_eligible_jobs()

    # Filter to only our test rows so real DB data doesn't interfere
    test_jobs = [j for j in jobs if j["url"].startswith(TEST_URL_PREFIX)]
    test_ids = {j["id"] for j in test_jobs}

    # Should include: eligible_high, eligible_low, eligible_retry1, eligible_retry2, applied_preset
    expected_included = {
        "eligible_high",
        "eligible_low",
        "eligible_retry1",
        "eligible_retry2",
        "applied_preset",
    }
    # Should exclude: ineligible_maxed (retry=3), ineligible_saved (status≠New)
    expected_excluded = {"ineligible_maxed", "ineligible_saved"}

    for label in expected_included:
        check(
            f"includes '{label}'",
            ids[label] in test_ids,
            f"id={ids[label]}",
        )

    for label in expected_excluded:
        check(
            f"excludes '{label}'",
            ids[label] not in test_ids,
            f"id={ids[label]}",
        )

    # Verify return type is list of dicts, not ORM objects
    check(
        "returns list of dicts",
        all(isinstance(j, dict) for j in test_jobs),
    )

    # Verify all required keys are present
    required_keys = {
        "id",
        "url",
        "title",
        "company",
        "score",
        "reasons",
        "scored_on",
        "auto_apply_ready",
        "retry_count",
        "status",
        "date_found",
        "applied_at",
        "last_attempted_at",
        "agent_failure_reason",
    }
    if test_jobs:
        missing = required_keys - test_jobs[0].keys()
        check("all required keys present", not missing, f"missing={missing}")

    # Verify ordering — scores should be descending among our test rows
    test_scores = [j["score"] for j in test_jobs]
    check(
        "ordered by score descending",
        test_scores == sorted(test_scores, reverse=True),
        f"scores={test_scores}",
    )


def test_mark_agent_applied_fresh(ids: dict[str, int]):
    print("\n── test_mark_agent_applied — fresh job (no prior applied_at) ──")

    job_id = ids["eligible_high"]
    before = datetime.utcnow()
    mark_agent_applied(job_id)
    after = datetime.utcnow()

    session = SessionLocal()
    try:
        job = fetch_job(session, job_id)

        check(
            "status set to 'Agent Applied'",
            job.status == "Agent Applied",
            f"got '{job.status}'",
        )

        check("applied_at is set", job.applied_at is not None)

        # applied_at should be between before and after (stamped during this call)
        if job.applied_at:
            applied_naive = (
                job.applied_at.replace(tzinfo=None)
                if job.applied_at.tzinfo
                else job.applied_at
            )
            check(
                "applied_at is recent",
                before <= applied_naive <= after,
                f"applied_at={job.applied_at}",
            )

        check("last_attempted_at is set", job.last_attempted_at is not None)

        if job.last_attempted_at:
            attempted_naive = (
                job.last_attempted_at.replace(tzinfo=None)
                if job.last_attempted_at.tzinfo
                else job.last_attempted_at
            )
            check(
                "last_attempted_at is recent",
                before <= attempted_naive <= after,
                f"last_attempted_at={job.last_attempted_at}",
            )

    finally:
        session.close()


def test_mark_agent_applied_preserves_applied_at(ids: dict[str, int]):
    print("\n── test_mark_agent_applied — preserves existing applied_at ────")

    job_id = ids["applied_preset"]
    original_applied_at = datetime(2025, 1, 15, 10, 0, 0)  # matches fixture

    mark_agent_applied(job_id)

    session = SessionLocal()
    try:
        job = fetch_job(session, job_id)

        check(
            "status set to 'Agent Applied'",
            job.status == "Agent Applied",
            f"got '{job.status}'",
        )

        # The original applied_at from the fixture must NOT be overwritten
        if job.applied_at:
            applied_naive = (
                job.applied_at.replace(tzinfo=None)
                if job.applied_at.tzinfo
                else job.applied_at
            )
            check(
                "original applied_at preserved",
                applied_naive == original_applied_at,
                f"expected={original_applied_at}, got={applied_naive}",
            )
        else:
            check("original applied_at preserved", False, "applied_at is None")

        check("last_attempted_at updated", job.last_attempted_at is not None)

    finally:
        session.close()


def test_mark_agent_failed_first_failure(ids: dict[str, int]):
    print("\n── test_mark_agent_failed — first failure (retry_count 0→1) ──")

    job_id = ids["eligible_low"]
    reason = "Login page blocked — could not find application form"

    before = datetime.utcnow()
    mark_agent_failed(job_id, reason)
    after = datetime.utcnow()

    session = SessionLocal()
    try:
        job = fetch_job(session, job_id)

        check(
            "status set to 'Agent Failed'",
            job.status == "Agent Failed",
            f"got '{job.status}'",
        )

        check(
            "agent_failure_reason stored",
            job.agent_failure_reason == reason,
            f"got '{job.agent_failure_reason}'",
        )

        check(
            "retry_count incremented to 1",
            job.retry_count == 1,
            f"got {job.retry_count}",
        )

        check("last_attempted_at is set", job.last_attempted_at is not None)

        if job.last_attempted_at:
            attempted_naive = (
                job.last_attempted_at.replace(tzinfo=None)
                if job.last_attempted_at.tzinfo
                else job.last_attempted_at
            )
            check(
                "last_attempted_at is recent",
                before <= attempted_naive <= after,
                f"last_attempted_at={job.last_attempted_at}",
            )

    finally:
        session.close()


def test_mark_agent_failed_increments_correctly(ids: dict[str, int]):
    print("\n── test_mark_agent_failed — retry_count increments correctly ──")

    # eligible_retry1 starts at retry_count=1, eligible_retry2 at retry_count=2
    cases = [
        ("eligible_retry1", 1, 2),  # (label, start, expected_after)
        ("eligible_retry2", 2, 3),
    ]

    for label, start, expected in cases:
        job_id = ids[label]
        mark_agent_failed(job_id, f"Test failure for {label}")

        session = SessionLocal()
        try:
            job = fetch_job(session, job_id)
            check(
                f"retry_count {start}→{expected} for '{label}'",
                job.retry_count == expected,
                f"got {job.retry_count}",
            )
        finally:
            session.close()


def test_mark_agent_failed_updates_reason_on_retry(ids: dict[str, int]):
    print("\n── test_mark_agent_failed — latest reason overwrites old one ──")

    # Use eligible_high which was already marked applied — reset it first
    # by directly setting status back to New so we can fail it
    job_id = ids["eligible_high"]
    session = SessionLocal()
    try:
        job = fetch_job(session, job_id)
        job.status = "New"
        job.retry_count = 0
        session.commit()
    finally:
        session.close()

    mark_agent_failed(job_id, "First failure reason")
    mark_agent_failed(job_id, "Second failure reason — most recent")

    session = SessionLocal()
    try:
        job = fetch_job(session, job_id)
        check(
            "reason updated to latest",
            job.agent_failure_reason == "Second failure reason — most recent",
            f"got '{job.agent_failure_reason}'",
        )
        check(
            "retry_count is 2 after two failures",
            job.retry_count == 2,
            f"got {job.retry_count}",
        )
    finally:
        session.close()


def test_eligible_jobs_excludes_after_failure(ids: dict[str, int]):
    print("\n── test_get_eligible_jobs — excludes 'Agent Failed' status ───")

    # eligible_low was just marked Agent Failed in a previous test — it should
    # NOT appear in get_eligible_jobs (wrong status)
    job_id = ids["eligible_low"]
    jobs = get_eligible_jobs()
    test_ids = {j["id"] for j in jobs}

    check(
        "'Agent Failed' job excluded from eligible list",
        job_id not in test_ids,
        f"job_id={job_id}",
    )


def test_invalid_job_id():
    print("\n── test invalid job_id raises ValueError ───────────────────────")

    fake_id = -999999

    try:
        mark_agent_applied(fake_id)
        check(
            "mark_agent_applied raises ValueError for bad id",
            False,
            "no exception raised",
        )
    except ValueError as e:
        check("mark_agent_applied raises ValueError for bad id", True, str(e))
    except Exception as e:
        check(
            "mark_agent_applied raises ValueError for bad id",
            False,
            f"wrong exception type: {type(e).__name__}: {e}",
        )

    try:
        mark_agent_failed(fake_id, "should fail")
        check(
            "mark_agent_failed raises ValueError for bad id",
            False,
            "no exception raised",
        )
    except ValueError as e:
        check("mark_agent_failed raises ValueError for bad id", True, str(e))
    except Exception as e:
        check(
            "mark_agent_failed raises ValueError for bad id",
            False,
            f"wrong exception type: {type(e).__name__}: {e}",
        )


# ── Runner ─────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  Agent DB Function Tests")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    ids: dict[str, int] = {}

    try:
        print("\n[Setup] Inserting test fixtures...")
        ids = insert_test_jobs()

        # Run all tests in order — some depend on state left by earlier tests
        test_get_eligible_jobs(ids)
        test_mark_agent_applied_fresh(ids)
        test_mark_agent_applied_preserves_applied_at(ids)
        test_mark_agent_failed_first_failure(ids)
        test_mark_agent_failed_increments_correctly(ids)
        test_mark_agent_failed_updates_reason_on_retry(ids)
        test_eligible_jobs_excludes_after_failure(ids)
        test_invalid_job_id()

    finally:
        print("\n[Teardown] Cleaning up test rows...")
        cleanup_test_jobs()

    # ── Summary ────────────────────────────────────────────────────────────────
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  |  {failed} FAILED:")
        for name, ok, detail in results:
            if not ok:
                print(f"    ✗ {name}" + (f" — {detail}" if detail else ""))
    else:
        print("  — all tests passed ✓")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
