import threading
import time
from typing import Optional

class ProgressTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: dict = {}

    def create(self, task_id: str):
        with self._lock:
            self._tasks[task_id] = {
                "stages": [],
                "current_stage": 0,
                "overall_progress": 0,
                "detail": "",
                "status": "pending",
                "result": None,
                "error": None,
                "yosys_passes": [],
                "yosys_pass_idx": -1,
                "updated_at": time.time()
            }

    def set_progress(self, task_id: str, pct: int, detail: str = ""):
        with self._lock:
            if task_id in self._tasks:
                t = self._tasks[task_id]
                t["overall_progress"] = min(pct, 100)
                if detail:
                    t["detail"] = detail
                t["updated_at"] = time.time()

    def next_yosys_pass(self, task_id: str, pass_name: str):
        with self._lock:
            if task_id in self._tasks:
                t = self._tasks[task_id]
                t["yosys_passes"].append(pass_name)
                t["yosys_pass_idx"] = len(t["yosys_passes"]) - 1

    def set_status(self, task_id: str, status: str, result=None, error=None):
        with self._lock:
            if task_id in self._tasks:
                t = self._tasks[task_id]
                t["status"] = status
                if result: t["result"] = result
                if error: t["error"] = error
                t["updated_at"] = time.time()

    def get(self, task_id: str) -> Optional[dict]:
        with self._lock:
            t = self._tasks.get(task_id)
            if t is None: return None
            return {
                "status": t["status"],
                "overall_progress": t["overall_progress"],
                "detail": t["detail"],
                "yosys_passes": t["yosys_passes"],
                "yosys_pass_idx": t["yosys_pass_idx"],
                "result": t["result"],
                "error": t["error"],
                "updated_at": t["updated_at"]
            }

progress = ProgressTracker()
