import pytest
import tempfile
import os
from backend.task_crud import TaskCRUD
from backend.models import TaskCreate, TaskUpdate

@pytest.fixture
def temp_crud():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    crud = TaskCRUD(db_path=path)
    yield crud
    try:
        os.remove(path)
    except Exception:
        pass

def test_task_crud_lifecycle(temp_crud):
    # 1. Create task
    t_create = TaskCreate(
        title="Test Room 302 Projectors",
        description="Verify dual 4K laser projectors with HDMI cable",
        due_date="2026-10-28 17:00",
        priority="High",
        category="Venue & AV",
        tags=["av", "room302"]
    )
    task = temp_crud.create_task(t_create)
    assert task.id.startswith("task-")
    assert task.title == "Test Room 302 Projectors"
    assert task.status == "pending"

    # 2. Get task
    retrieved = temp_crud.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id

    # 3. Update task
    updated = temp_crud.update_task(task.id, TaskUpdate(priority="Urgent", status="in_progress"))
    assert updated.priority == "Urgent"
    assert updated.status == "in_progress"

    # 4. Toggle status
    toggled = temp_crud.toggle_status(task.id)
    assert toggled.status == "completed"

    # 5. List with filters
    all_tasks = temp_crud.list_tasks()
    assert len(all_tasks) == 1
    completed_tasks = temp_crud.list_tasks(status="completed")
    assert len(completed_tasks) == 1
    pending_tasks = temp_crud.list_tasks(status="pending")
    assert len(pending_tasks) == 0

    # 6. Stats
    stats = temp_crud.get_stats()
    assert stats["total"] == 1
    assert stats["completed"] == 1
    assert stats["completion_pct"] == 100.0

    # 7. Delete
    deleted = temp_crud.delete_task(task.id)
    assert deleted is True
    assert temp_crud.get_task(task.id) is None

if __name__ == "__main__":
    pytest.main(["-v", __file__])
