"""
Test script for the new database layer (Supabase + SQLite fallback).
Run with: venv\Scripts\python test_database.py
"""
import sys
sys.path.insert(0, '.')

from app.database import (
    init_db, using_supabase,
    upsert_user, get_user_by_student_id,
    insert_queue_item, get_pending_queue_items, update_queue_item_status,
    insert_log, get_logs,
)

def main():
    print("=== DATABASE LAYER TEST ===")
    print(f"Mode: {'Supabase' if using_supabase() else 'SQLite (fallback)'}")

    # Init
    init_db()
    print("1. DB init OK")

    # Upsert user
    u1 = upsert_user("STU001")
    print(f"2. Created user: {u1}")
    assert u1 is not None, "Failed to create user"

    # Duplicate upsert (should return existing)
    u2 = upsert_user("STU001")
    print(f"3. Duplicate user: {u2}")
    assert u2 is not None, "Failed on duplicate user"

    # Get user
    u3 = get_user_by_student_id("STU001")
    print(f"4. Get user: {u3}")

    # Queue items
    q1 = insert_queue_item("STU001", "/images/stu001_1.jpg")
    print(f"5. Insert queue item: {q1}")
    assert q1 == True, "Failed to insert queue item"

    q2 = insert_queue_item("STU001", "/images/stu001_2.jpg")
    print(f"6. Insert queue item 2: {q2}")

    # Get pending
    pending = get_pending_queue_items()
    print(f"7. Pending items: {len(pending)}")
    for p in pending:
        print(f"   - ID={p['id']}, student={p['student_id']}, path={p['image_path']}")

    # Update status
    if pending:
        updated = update_queue_item_status(pending[0]["id"], "completed")
        print(f"8. Update status completed: {updated}")

    # Check remaining pending
    remaining = get_pending_queue_items()
    print(f"9. Remaining pending: {len(remaining)}")

    # Insert log
    log_ok = insert_log("STU001", 0.85, "ESP32-01")
    print(f"10. Insert log: {log_ok}")

    # Insert no-match log
    log_ok2 = insert_log(None, 0.0, "ESP32-01")
    print(f"11. Insert no-match log: {log_ok2}")

    # Get logs
    logs = get_logs(10)
    print(f"12. Get logs count: {len(logs)}")
    for log in logs[:3]:
        print(f"    - student={log.get('student_id')}, score={log.get('similarity_score')}")

    # Cleanup test data (SQLite mode only)
    if not using_supabase():
        from app.database import _get_sqlite_session, _QueueModel, _LogModel, _UserModel
        session = next(_get_sqlite_session())
        try:
            session.query(_QueueModel).delete()
            session.query(_LogModel).delete()
            session.query(_UserModel).filter(_UserModel.student_id == "STU001").delete()
            session.commit()
            print("13. Cleanup OK")
        finally:
            session.close()

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    main()