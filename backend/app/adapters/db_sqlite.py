import sqlite3
import json
from typing import List, Optional
from app.domain.models import ScenarioMatrix, UserPreferenceProfile
from app.ports.repository import TripRepositoryPort

class SQLiteTripRepository(TripRepositoryPort):
    def __init__(self, db_path: str = "kompass.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scenario_matrices (
                    session_id TEXT PRIMARY KEY,
                    matrix_data TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT
                )
            ''')
            conn.commit()

    async def get_user_profile(self, user_id: str) -> Optional[UserPreferenceProfile]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT profile_data FROM user_profiles WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return UserPreferenceProfile(**data)
        return None

    async def save_user_profile(self, profile: UserPreferenceProfile) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO user_profiles (user_id, profile_data) VALUES (?, ?)',
                (profile.user_id, profile.model_dump_json())
            )

    async def save_scenario_matrix(self, session_id: str, matrix: ScenarioMatrix) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO scenario_matrices (session_id, matrix_data) VALUES (?, ?)',
                (session_id, matrix.model_dump_json())
            )

    async def get_scenario_matrix(self, session_id: str) -> Optional[ScenarioMatrix]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT matrix_data FROM scenario_matrices WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return ScenarioMatrix(**data)
        return None

    async def append_message(self, session_id: str, role: str, content: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)',
                (session_id, role, content)
            )

    async def get_messages(self, session_id: str) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC', (session_id,))
            rows = cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]
