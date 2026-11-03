import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.config import DATABASE_PATH
from backend.models import Task, TaskCreate, TaskUpdate

class TaskCRUD:
    """Persistent SQLite database manager for Task CRUD API operations."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DATABASE_PATH)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    priority TEXT DEFAULT 'Medium',
                    priority_reason TEXT,
                    category TEXT DEFAULT 'General',
                    status TEXT DEFAULT 'pending',
                    tags TEXT,
                    source_notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        tags = json.loads(row["tags"]) if row["tags"] else []
        source_notes = json.loads(row["source_notes"]) if row["source_notes"] else []
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            due_date=row["due_date"] or "",
            priority=row["priority"] or "Medium",
            priority_reason=row["priority_reason"],
            category=row["category"] or "General",
            status=row["status"] or "pending",
            tags=tags,
            source_notes=source_notes,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def create_task(self, task: TaskCreate) -> Task:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        tags_json = json.dumps(task.tags)
        source_notes_json = json.dumps(task.source_notes)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    id, title, description, due_date, priority, priority_reason,
                    category, status, tags, source_notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, task.title, task.description, task.due_date,
                task.priority, task.priority_reason, task.category,
                task.status, tags_json, source_notes_json, now, now
            ))
            conn.commit()

        return self.get_task(task_id)

    def create_batch(self, tasks: List[TaskCreate]) -> List[Task]:
        created = []
        for t in tasks:
            created.append(self.create_task(t))
        return created

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            if row:
                return self._row_to_task(row)
        return None

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Task]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: List[Any] = []

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)

        if priority and priority != "all":
            query += " AND priority = ?"
            params.append(priority)

        if category and category != "all":
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])

        query += " ORDER BY created_at DESC"

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [self._row_to_task(r) for r in rows]

    def update_task(self, task_id: str, updates: TaskUpdate) -> Optional[Task]:
        existing = self.get_task(task_id)
        if not existing:
            return None

        update_fields = []
        params = []

        if updates.title is not None:
            update_fields.append("title = ?")
            params.append(updates.title)
        if updates.description is not None:
            update_fields.append("description = ?")
            params.append(updates.description)
        if updates.due_date is not None:
            update_fields.append("due_date = ?")
            params.append(updates.due_date)
        if updates.priority is not None:
            update_fields.append("priority = ?")
            params.append(updates.priority)
        if updates.priority_reason is not None:
            update_fields.append("priority_reason = ?")
            params.append(updates.priority_reason)
        if updates.category is not None:
            update_fields.append("category = ?")
            params.append(updates.category)
        if updates.status is not None:
            update_fields.append("status = ?")
            params.append(updates.status)
        if updates.tags is not None:
            update_fields.append("tags = ?")
            params.append(json.dumps(updates.tags))
        if updates.source_notes is not None:
            update_fields.append("source_notes = ?")
            params.append(json.dumps(updates.source_notes))

        if not update_fields:
            return existing

        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(task_id)

        sql = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
        with self._get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()

        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0

    def toggle_status(self, task_id: str) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        cycle = {"pending": "in_progress", "in_progress": "completed", "completed": "pending"}
        new_status = cycle.get(task.status, "pending")
        return self.update_task(task_id, TaskUpdate(status=new_status))

    def get_stats(self) -> Dict[str, Any]:
        tasks = self.list_tasks()
        total = len(tasks)
        pending = sum(1 for t in tasks if t.status == "pending")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        completed = sum(1 for t in tasks if t.status == "completed")
        urgent = sum(1 for t in tasks if t.priority == "Urgent")
        high = sum(1 for t in tasks if t.priority == "High")

        categories: Dict[str, int] = {}
        for t in tasks:
            cat = t.category or "General"
            categories[cat] = categories.get(cat, 0) + 1

        completion_pct = round((completed / total * 100), 1) if total > 0 else 0.0

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "urgent": urgent,
            "high": high,
            "completion_pct": completion_pct,
            "categories": categories
        }

    def clear_all(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM tasks")
            conn.commit()

# Global singleton
_crud_instance: Optional[TaskCRUD] = None

def get_task_crud() -> TaskCRUD:
    global _crud_instance
    if _crud_instance is None:
        _crud_instance = TaskCRUD()
    return _crud_instance
