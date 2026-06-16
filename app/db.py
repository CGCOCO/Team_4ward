import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "app_data.sqlite3"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _drop_pdf_url_column(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(analysis_results)").fetchall()
    if not any(column["name"] == "pdf_url" for column in columns):
        return

    conn.executescript(
        """
        CREATE TABLE analysis_results_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_url TEXT,
            ai_result TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        INSERT INTO analysis_results_new (
            id,
            user_id,
            image_url,
            ai_result,
            created_at,
            updated_at
        )
        SELECT
            id,
            user_id,
            image_url,
            ai_result,
            created_at,
            updated_at
        FROM analysis_results;

        DROP TABLE analysis_results;
        ALTER TABLE analysis_results_new RENAME TO analysis_results;
        """
    )


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                image_url TEXT,
                ai_result TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_analysis_results_user_id
                ON analysis_results(user_id);
            """
        )
        _drop_pdf_url_column(conn)
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_analysis_results_user_id
                ON analysis_results(user_id)
            """
        )
