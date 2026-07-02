class TaskConflictError(Exception):
    """Raised when a new task overlaps with an already-scheduled task."""

    def __init__(self, conflicting_task_id: str, conflicting_task_title: str) -> None:
        self.conflicting_task_id = conflicting_task_id
        self.conflicting_task_title = conflicting_task_title
        super().__init__(f"Time conflict with '{conflicting_task_title}'")
