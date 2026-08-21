"""Celery queue abstraction layer - initialized via FastAPI lifespan."""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CeleryQueue:
    """
    Singleton class that abstracts Celery queue operations.
    
    Initialized via FastAPI lifespan in public_api, allowing loose coupling
    between the API and Celery worker processes.
    
    The celery_app is injected at initialization time, not imported lazily.
    This ensures early error detection if Celery is unavailable.
    """

    _instance: Optional["CeleryQueue"] = None
    _celery_app: Any = None

    def __new__(cls) -> "CeleryQueue":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls, celery_app: Any) -> None:
        """
        Initialize the singleton with a Celery app instance.
        Called during FastAPI startup (via lifespan context manager).
        
        Args:
            celery_app: Celery application instance
            
        Raises:
            RuntimeError: If already initialized
        """
        if cls._celery_app is not None:
            logger.warning("CeleryQueue already initialized, skipping re-initialization")
            return
        cls._celery_app = celery_app
        logger.info("CeleryQueue initialized with celery_app")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the queue has been initialized."""
        return cls._celery_app is not None

    @staticmethod
    def _get_app() -> Any:
        """Get the celery_app. Raises if not initialized."""
        if CeleryQueue._celery_app is None:
            raise RuntimeError(
                "CeleryQueue not initialized. Call CeleryQueue.init(celery_app) "
                "during application startup (e.g., in FastAPI lifespan)."
            )
        return CeleryQueue._celery_app

    def send_task(self, task_name: str, args: tuple = ()) -> Any:
        """
        Send a task to the queue.
        
        Args:
            task_name: Fully qualified task name (e.g., "src.services.ingestion.tasks.process_document_task")
            args: Positional arguments to pass to the task
            
        Returns:
            AsyncResult object for tracking the task
        """
        app = self._get_app()
        return app.send_task(task_name, args=args)

    def revoke_task(self, task_id: str, terminate: bool = False) -> None:
        """
        Revoke (cancel) a task.
        
        Args:
            task_id: ID of the task to revoke
            terminate: If True, terminate the task immediately if running
        """
        app = self._get_app()
        app.control.revoke(task_id, terminate=terminate)
        logger.debug(f"Task {task_id} revoked (terminate={terminate})")

    def get_task_result(self, task_id: Optional[str]) -> Any:
        """
        Get the result/state of a task by its ID.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            AsyncResult object, or None if task_id is None
        """
        if task_id is None:
            return None
        app = self._get_app()
        return app.AsyncResult(task_id)


def get_queue() -> CeleryQueue:
    """Get the singleton CeleryQueue instance."""
    return CeleryQueue()
