import os
import shutil
import sqlite3
import datetime
import logging
from app.core.config import settings
from app.core.security import hash_password

logger = logging.getLogger(__name__)

def migrate_database():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../civiclens.db"))
    if not os.path.exists(db_path):
        logger.info(f"Database file {db_path} does not exist yet. Migration skipped.")
        return

    # 1. Backup existing database
    backup_path = f"{db_path}.bak"
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up successfully to {backup_path}")
    except Exception as e:
        logger.warning(f"Could not backup database: {e}")

    # 2. Connect and inspect columns
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR PRIMARY KEY,
        email VARCHAR UNIQUE NOT NULL,
        hashed_password VARCHAR NOT NULL,
        full_name VARCHAR NOT NULL,
        role VARCHAR NOT NULL DEFAULT 'CITIZEN',
        department VARCHAR,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create ai_feedback table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_feedback (
        id VARCHAR PRIMARY KEY,
        incident_id VARCHAR NOT NULL,
        ai_category VARCHAR NOT NULL,
        final_category VARCHAR NOT NULL,
        ai_confidence FLOAT DEFAULT 1.0,
        reason TEXT,
        reviewer_id VARCHAR,
        reviewer_email VARCHAR,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(incident_id) REFERENCES incidents(id),
        FOREIGN KEY(reviewer_id) REFERENCES users(id)
    );
    """)

    # Check work_orders table columns
    cursor.execute("PRAGMA table_info(work_orders);")
    wo_cols = [row[1] for row in cursor.fetchall()]

    wo_new_cols = [
        ("assigned_team", "VARCHAR"),
        ("assigned_worker", "VARCHAR"),
        ("assigned_worker_id", "VARCHAR"),
        ("sla_deadline", "DATETIME"),
        ("sla_status", "VARCHAR DEFAULT 'ON_TRACK'"),
        ("assigned_at", "DATETIME"),
        ("started_at", "DATETIME"),
    ]

    for col_name, col_type in wo_new_cols:
        if col_name not in wo_cols:
            logger.info(f"Adding missing column '{col_name}' to work_orders table...")
            cursor.execute(f"ALTER TABLE work_orders ADD COLUMN {col_name} {col_type};")

    # Check incidents table columns
    cursor.execute("PRAGMA table_info(incidents);")
    inc_cols = [row[1] for row in cursor.fetchall()]

    inc_new_cols = [
        ("verification_notes", "TEXT"),
        ("ai_category", "VARCHAR"),
        ("ai_confidence", "FLOAT DEFAULT 1.0"),
        ("ai_department", "VARCHAR"),
        ("confidence_tier", "VARCHAR DEFAULT 'HIGH'"),
        ("requires_human_review", "BOOLEAN DEFAULT 0"),
        ("review_status", "VARCHAR DEFAULT 'ACCEPTED'"),
        ("review_reason", "TEXT"),
        ("reviewed_by", "VARCHAR"),
        ("reviewed_at", "DATETIME")
    ]

    for col_name, col_type in inc_new_cols:
        if col_name not in inc_cols:
            logger.info(f"Adding missing column '{col_name}' to incidents table...")
            cursor.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_type};")

    conn.commit()

    # Seed default authenticated demo users if missing
    cursor.execute("SELECT COUNT(*) FROM users;")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        logger.info("Seeding default authenticated demo users...")
        now_str = datetime.datetime.utcnow().isoformat()
        demo_users = [
            ("usr-citizen-1", "citizen@civiclens.local", hash_password("Citizen123!"), "Citizen User", "CITIZEN", None, now_str),
            ("usr-dispatcher-1", "dispatcher@civiclens.local", hash_password("Dispatcher123!"), "Dispatcher Operator", "DISPATCHER", None, now_str),
            ("usr-crew-1", "crew@civiclens.local", hash_password("Crew123!"), "Road Worker Alpha", "FIELD_CREW", "Public Works - Roads", now_str),
            ("usr-crew-2", "crew_beta@civiclens.local", hash_password("Crew123!"), "Road Worker Beta", "FIELD_CREW", "Public Works - Roads", now_str),
            ("usr-crew-water", "crew_water@civiclens.local", hash_password("Crew123!"), "Water Department Crew Worker", "FIELD_CREW", "Water Department", now_str),
            ("usr-crew-traffic", "crew_traffic@civiclens.local", hash_password("Crew123!"), "Traffic Management Crew Worker", "FIELD_CREW", "Traffic Management", now_str),
            ("usr-crew-electrical", "crew_electrical@civiclens.local", hash_password("Crew123!"), "Electrical Maintenance Crew Worker", "FIELD_CREW", "Electrical Maintenance", now_str),
            ("usr-crew-drainage", "crew_drainage@civiclens.local", hash_password("Crew123!"), "Drainage & Sewer Crew Worker", "FIELD_CREW", "Drainage & Sewer", now_str),
            ("usr-crew-sanitation", "crew_sanitation@civiclens.local", hash_password("Crew123!"), "Waste Management Crew Worker", "FIELD_CREW", "Waste Management", now_str)
        ]
        cursor.executemany("""
        INSERT INTO users (id, email, hashed_password, full_name, role, department, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, demo_users)
        conn.commit()

    # Data Repair: Ensure any ASSIGNED, IN_PROGRESS, or COMPLETED WorkOrder has non-null assigned_team and assigned_worker
    cursor.execute("""
    UPDATE work_orders 
    SET assigned_team = 'Road Maintenance Crew Alpha', 
        assigned_worker = 'Field Crew Worker',
        assigned_at = COALESCE(assigned_at, CURRENT_TIMESTAMP)
    WHERE status IN ('ASSIGNED', 'IN_PROGRESS', 'COMPLETED') 
      AND (assigned_team IS NULL OR assigned_worker IS NULL);
    """)
    repaired_count = cursor.rowcount
    if repaired_count > 0:
        logger.info(f"Data Repair: Repaired {repaired_count} WorkOrders with missing assignment fields.")
    conn.commit()

    conn.close()
    logger.info("Database schema migration and user seeding completed successfully!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_database()
