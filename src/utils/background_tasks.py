"""Background task manager for running searches without blocking the UI."""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger("BackgroundTasks")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    task_type: str
    started_at: str
    completed_at: Optional[str] = None
    progress: int = 0
    progress_message: str = ""
    result_count: int = 0
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class BackgroundTaskManager:
    """Manages background tasks for the application."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tasks_file = Path("data/background_tasks.json")
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_task: Optional[threading.Thread] = None
        self._stop_requested = False

    def _load_tasks(self) -> dict:
        """Load tasks from file."""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"current_task": None, "history": []}

    def _save_task(self, task: TaskResult):
        """Save task status to file."""
        data = self._load_tasks()
        data["current_task"] = task.to_dict()
        with open(self.tasks_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_current_task(self) -> Optional[TaskResult]:
        """Get the current running or last completed task."""
        data = self._load_tasks()
        if data.get("current_task"):
            task_data = data["current_task"]
            return TaskResult(
                task_id=task_data.get("task_id", ""),
                status=TaskStatus(task_data.get("status", "pending")),
                task_type=task_data.get("task_type", ""),
                started_at=task_data.get("started_at", ""),
                completed_at=task_data.get("completed_at"),
                progress=task_data.get("progress", 0),
                progress_message=task_data.get("progress_message", ""),
                result_count=task_data.get("result_count", 0),
                error=task_data.get("error")
            )
        return None

    def is_task_running(self) -> bool:
        """Check if a task is currently running."""
        task = self.get_current_task()
        return task is not None and task.status == TaskStatus.RUNNING

    def update_progress(self, task_id: str, progress: int, message: str = ""):
        """Update task progress."""
        task = self.get_current_task()
        if task and task.task_id == task_id:
            task.progress = progress
            task.progress_message = message
            self._save_task(task)

    def complete_task(self, task_id: str, result_count: int):
        """Mark task as completed."""
        task = self.get_current_task()
        if task and task.task_id == task_id:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.progress = 100
            task.result_count = result_count
            task.progress_message = f"Completed! Found {result_count} leads"
            self._save_task(task)
            logger.info(f"Task {task_id} completed with {result_count} results")

    def fail_task(self, task_id: str, error: str):
        """Mark task as failed."""
        task = self.get_current_task()
        if task and task.task_id == task_id:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().isoformat()
            task.error = error
            task.progress_message = f"Error: {error}"
            self._save_task(task)
            logger.error(f"Task {task_id} failed: {error}")

    def start_search_task(self, search_func: Callable, task_type: str = "lead_search") -> str:
        """Start a search task in the background."""
        if self.is_task_running():
            logger.warning("A task is already running")
            return ""

        task_id = f"task_{int(time.time())}"
        task = TaskResult(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            task_type=task_type,
            started_at=datetime.now().isoformat(),
            progress=0,
            progress_message="Starting search..."
        )
        self._save_task(task)

        # Start in background thread
        def run_task():
            try:
                search_func(task_id)
            except Exception as e:
                self.fail_task(task_id, str(e))

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        self._current_task = thread

        logger.info(f"Started background task: {task_id}")
        return task_id

    def clear_completed_task(self):
        """Clear the current task if it's completed."""
        task = self.get_current_task()
        if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            data = self._load_tasks()
            # Move to history
            if "history" not in data:
                data["history"] = []
            data["history"].insert(0, data["current_task"])
            data["history"] = data["history"][:10]  # Keep last 10
            data["current_task"] = None
            with open(self.tasks_file, 'w') as f:
                json.dump(data, f, indent=2)


# Singleton instance
task_manager = BackgroundTaskManager()
