#!/usr/bin/env python3
# /home/claude/task_queue.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class ScanPhase(Enum):
    DISCOVERY = 1
    ENUMERATION = 2
    WEB_TESTING = 3
    EXPLOITATION = 4
    POST_EXPLOIT = 5

@dataclass
class ScanTask:
    phase: ScanPhase
    target: str
    tool: str
    priority: int
    ports: Optional[List[int]] = None
    options: Optional[dict] = None
    dependencies: Optional[List[str]] = None

class TaskQueue:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def add_task(self, task: ScanTask):
        """Add task to appropriate queue based on phase"""
        queue_name = f"queue:{task.phase.name.lower()}"
        self.redis.lpush(queue_name, json.dumps(task.__dict__))
    
    def get_next_task(self, phase: ScanPhase) -> Optional[ScanTask]:
        """Get next task for a specific phase"""
        queue_name = f"queue:{phase.name.lower()}"
        task_data = self.redis.rpop(queue_name)
        
        if task_data:
            return ScanTask(**json.loads(task_data))
        return None
    
    def mark_complete(self, task_id: str):
        """Mark task as completed"""
        self.redis.sadd("completed_tasks

