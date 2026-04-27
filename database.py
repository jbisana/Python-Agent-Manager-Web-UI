import sqlite3
import time
from contextlib import contextmanager
from config import Config

def init_db():
    with sqlite3.connect(Config.DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                script_key  TEXT NOT NULL,
                started_at  REAL NOT NULL,
                ended_at    REAL,
                status      TEXT NOT NULL DEFAULT 'running',
                elapsed     TEXT,
                exit_code   INTEGER,
                stop_reason TEXT
            )
        """)
        try:
            con.execute("ALTER TABLE runs ADD COLUMN stop_reason TEXT")
        except sqlite3.OperationalError:
            pass
        con.execute("CREATE INDEX IF NOT EXISTS idx_runs_key ON runs(script_key)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at DESC)")
        con.commit()

@contextmanager
def get_db():
    con = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def db_insert_run(run_id: str, key: str, started_at: float):
    with get_db() as con:
        con.execute(
            "INSERT INTO runs (run_id, script_key, started_at, status) VALUES (?,?,?,?)",
            (run_id, key, started_at, "running"),
        )

def db_finish_run(run_id: str, status: str, elapsed: str,
                  exit_code: int | None, stop_reason: str | None = None):
    with get_db() as con:
        con.execute(
            "UPDATE runs SET ended_at=?, status=?, elapsed=?, exit_code=?, stop_reason=? "
            "WHERE run_id=?",
            (time.time(), status, elapsed, exit_code, stop_reason, run_id),
        )

def db_get_run_history(key: str, limit: int = 20) -> list:
    with get_db() as con:
        rows = con.execute(
            "SELECT * FROM runs WHERE script_key=? ORDER BY started_at DESC LIMIT ?",
            (key, limit),
        ).fetchall()
    return [dict(r) for r in rows]

def db_get_all_last_runs() -> dict:
    with get_db() as con:
        rows = con.execute("""
            SELECT r.*
            FROM runs r
            INNER JOIN (
                SELECT script_key, MAX(started_at) AS max_ts
                FROM runs GROUP BY script_key
            ) latest ON r.script_key = latest.script_key AND r.started_at = latest.max_ts
        """).fetchall()
    return {row["script_key"]: dict(row) for row in rows}

def db_get_script_stats(key: str) -> dict:
    with get_db() as con:
        # We need to parse the elapsed string "X.Xs" to a float
        # or calculate it from started_at/ended_at
        row = con.execute("""
            SELECT 
                COUNT(*) as total_runs,
                AVG(CASE WHEN ended_at IS NOT NULL THEN (ended_at - started_at) ELSE NULL END) as avg_duration,
                MAX(CASE WHEN ended_at IS NOT NULL THEN (ended_at - started_at) ELSE NULL END) as max_duration,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
            FROM runs WHERE script_key=?
        """, (key,)).fetchone()
    
    if not row or row["total_runs"] == 0:
        return {"total_runs": 0, "avg_duration": 0, "max_duration": 0, "error_count": 0}
        
    return {
        "total_runs": row["total_runs"],
        "avg_duration": round(row["avg_duration"] or 0, 1),
        "max_duration": round(row["max_duration"] or 0, 1),
        "error_count": row["error_count"]
    }
