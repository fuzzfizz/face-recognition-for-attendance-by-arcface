#!/usr/bin/env python3
"""
MySQL Connection and Database Operations Verification Tool.
Tests connecting to MySQL (or local SQLite fallback) and verifies CRUD + BLOB operations.

Usage:
  python connection_test.py [--sqlite] [--host HOST] [--port PORT] [--user USER] [--password PASSWORD] [--database DATABASE]
"""

import sys
import argparse
import datetime
import os

# Attempt to import MySQL connector
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    MySQLError = Exception

import sqlite3

# ANSI colors for nice terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_step(msg):
    print(f"\n{CYAN}{BOLD}>> {msg}{RESET}")

def print_success(msg):
    print(f"{GREEN}[OK] {msg}{RESET}")

def print_error(msg):
    print(f"{RED}[ERROR] {msg}{RESET}", file=sys.stderr)

def print_info(msg):
    print(f"{YELLOW}[INFO] {msg}{RESET}")

def parse_args():
    parser = argparse.ArgumentParser(description="Test MySQL connection and database operations.")
    parser.add_argument("--sqlite", action="store_true", help="Use local SQLite database for local test run.")
    parser.add_argument("--host", default="localhost", help="MySQL host (default: localhost)")
    parser.add_argument("--port", type=int, default=3306, help="MySQL port (default: 3306)")
    parser.add_argument("--user", default="face_admin", help="MySQL user (default: face_admin)")
    parser.add_argument("--password", default="SecurePassword123!", help="MySQL password")
    parser.add_argument("--database", default="face_attendance", help="MySQL database name (default: face_attendance)")
    return parser.parse_args()

class DatabaseAdapter:
    def __init__(self, args):
        self.args = args
        self.db_type = "sqlite" if args.sqlite else "mysql"
        self.conn = None
        self.cursor = None

    def connect(self):
        if self.db_type == "sqlite":
            print_info("Connecting to local SQLite database: test_local.db")
            self.conn = sqlite3.connect("test_local.db")
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            # Enable foreign keys for SQLite
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            self.create_sqlite_schema()
        else:
            if not HAS_MYSQL:
                raise ImportError(
                    "mysql-connector-python is not installed. "
                    "Install it using: pip install mysql-connector-python"
                )
            print_info(f"Connecting to MySQL at {self.args.host}:{self.args.port} (DB: {self.args.database}, User: {self.args.user})...")
            self.conn = mysql.connector.connect(
                host=self.args.host,
                port=self.args.port,
                user=self.args.user,
                password=self.args.password,
                database=self.args.database
            )
            self.cursor = self.conn.cursor(dictionary=True)

    def create_sqlite_schema(self):
        """Creates the identical schema in SQLite for local testing verification."""
        print_info("Initializing temporary SQLite tables...")
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_users_student_id ON users (student_id);

        CREATE TABLE IF NOT EXISTS registration_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            image_blob BLOB NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP NULL
        );
        CREATE INDEX IF NOT EXISTS idx_registration_queue_student_id ON registration_queue (student_id);
        CREATE INDEX IF NOT EXISTS idx_registration_queue_status ON registration_queue (status);

        CREATE TABLE IF NOT EXISTS check_in_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NULL,
            student_id TEXT NULL,
            similarity_score REAL NULL,
            device_id TEXT NULL,
            error_message TEXT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_check_in_logs_timestamp ON check_in_logs (timestamp DESC);
        """)
        self.conn.commit()

    def execute(self, query, params=None):
        # Convert %s placeholders to ? if SQLite
        if self.db_type == "sqlite":
            query = query.replace("%s", "?")
        
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)

    def fetchone(self):
        row = self.cursor.fetchone()
        if not row:
            return None
        # Convert to dict if SQLite Row
        if self.db_type == "sqlite" and isinstance(row, sqlite3.Row):
            return dict(row)
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.db_type == "sqlite":
            return [dict(r) for r in rows]
        return rows

    def last_insert_id(self):
        return self.cursor.lastrowid

    def commit(self):
        self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        if self.db_type == "sqlite" and os.path.exists("test_local.db"):
            try:
                os.remove("test_local.db")
                print_info("Cleaned up temporary SQLite database file test_local.db")
            except Exception as e:
                print_info(f"Could not delete test_local.db: {e}")

def main():
    args = parse_args()
    
    if not args.sqlite and not HAS_MYSQL:
        print_error("mysql-connector-python package is missing.")
        print_info("To test MySQL connections, install the connector via:")
        print_info("  pip install mysql-connector-python")
        print_info("Or run in SQLite verification mode:")
        print_info("  python connection_test.py --sqlite")
        sys.exit(1)

    db = DatabaseAdapter(args)
    try:
        print_step("Connecting to database")
        db.connect()
        print_success("Database connection established successfully.")

        # Step 1: User Insertion
        print_step("Testing: User Table CRUD")
        student_id = "test_student_999"
        student_name = "Test Student Name"
        
        # Cleanup any leftover from failed previous run
        db.execute("DELETE FROM users WHERE student_id = %s", (student_id,))
        db.commit()

        db.execute(
            "INSERT INTO users (student_id, name) VALUES (%s, %s)",
            (student_id, student_name)
        )
        db.commit()
        user_id = db.last_insert_id()
        print_success(f"Inserted test user with ID: {user_id}")

        # Fetch and verify user
        db.execute("SELECT * FROM users WHERE student_id = %s", (student_id,))
        user = db.fetchone()
        assert user is not None, "Failed to retrieve inserted user."
        assert user["name"] == student_name, f"Expected name {student_name}, got {user['name']}"
        print_success(f"Verified user data: student_id={user['student_id']}, name={user['name']}")

        # Step 2: Registration Queue BLOB & Status Update
        print_step("Testing: Registration Queue & BLOB")
        queue_student_id = "pending_student_888"
        
        # Create a mock 100-byte binary blob
        mock_image_data = bytes([i % 256 for i in range(100)])
        
        # Cleanup potential leftover
        db.execute("DELETE FROM registration_queue WHERE student_id = %s", (queue_student_id,))
        db.commit()

        db.execute(
            "INSERT INTO registration_queue (student_id, image_blob, status) VALUES (%s, %s, %s)",
            (queue_student_id, mock_image_data, "pending")
        )
        db.commit()
        queue_id = db.last_insert_id()
        print_success(f"Inserted registration queue item with ID: {queue_id}")

        # Verify status is pending
        db.execute("SELECT * FROM registration_queue WHERE id = %s", (queue_id,))
        queue_row = db.fetchone()
        assert queue_row is not None, "Failed to retrieve queue item."
        assert queue_row["status"] == "pending", f"Expected status 'pending', got {queue_row['status']}"
        print_success("Verified queue item status is 'pending'")

        # Update status
        now = datetime.datetime.now()
        db.execute(
            "UPDATE registration_queue SET status = %s, processed_at = %s, error_message = %s WHERE id = %s",
            ("processed", now, "No error", queue_id)
        )
        db.commit()
        
        db.execute("SELECT * FROM registration_queue WHERE id = %s", (queue_id,))
        queue_row_updated = db.fetchone()
        assert queue_row_updated["status"] == "processed", f"Expected status 'processed', got {queue_row_updated['status']}"
        assert queue_row_updated["error_message"] == "No error", "Expected error_message 'No error'"
        print_success("Verified queue item status updated to 'processed' and error_message set.")

        # Step 3: Check-in Logs Table
        print_step("Testing: Check-in Logs")
        device_id = "test_device_55"
        similarity = 0.897
        error_msg = "Verification successful"

        db.execute(
            "INSERT INTO check_in_logs (user_id, student_id, similarity_score, device_id, error_message) VALUES (%s, %s, %s, %s, %s)",
            (user_id, student_id, similarity, device_id, error_msg)
        )
        db.commit()
        log_id = db.last_insert_id()
        print_success(f"Inserted check-in log with ID: {log_id}")

        db.execute("SELECT * FROM check_in_logs WHERE id = %s", (log_id,))
        log_row = db.fetchone()
        assert log_row is not None, "Failed to retrieve log item."
        assert abs(log_row["similarity_score"] - similarity) < 0.0001, f"Expected similarity {similarity}, got {log_row['similarity_score']}"
        assert log_row["device_id"] == device_id, f"Expected device {device_id}, got {log_row['device_id']}"
        print_success("Verified check-in log values successfully.")

        # Step 4: Clean Up
        print_step("Testing: Clean up & cascade verification")
        
        # Deleting the user should cascade set NULL on check_in_logs
        db.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
        print_success("Deleted test user.")

        # Verify check_in_logs user_id set to NULL (due to ON DELETE SET NULL)
        db.execute("SELECT * FROM check_in_logs WHERE id = %s", (log_id,))
        log_after_delete = db.fetchone()
        assert log_after_delete is not None, "Log row was deleted, but should have been kept."
        assert log_after_delete["user_id"] is None, f"Expected user_id to be NULL (SET NULL), got {log_after_delete['user_id']}"
        print_success("Verified check-in log user_id was set to NULL (ON DELETE SET NULL)")

        # Manually delete remaining test data (queue and log)
        db.execute("DELETE FROM registration_queue WHERE id = %s", (queue_id,))
        db.execute("DELETE FROM check_in_logs WHERE id = %s", (log_id,))
        db.commit()
        print_success("Cleaned up remaining test entries.")

        print(f"\n{GREEN}{BOLD}=== ALL TESTS PASSED SUCCESSFULLY ==={RESET}")

    except AssertionError as e:
        print_error(f"Assertion Error: {e}")
        db.rollback()
        sys.exit(2)
    except MySQLError as e:
        print_error(f"Database Error: {e}")
        db.rollback()
        sys.exit(3)
    except Exception as e:
        print_error(f"Unexpected Error: {e}")
        db.rollback()
        sys.exit(4)
    finally:
        db.close()

if __name__ == "__main__":
    main()
