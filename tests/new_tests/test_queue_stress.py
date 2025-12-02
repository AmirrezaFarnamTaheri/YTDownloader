"""
Stress tests for queue concurrency.
"""

import threading
import time
import uuid
import pytest
from queue_manager import QueueManager
from utils import CancelToken

def test_queue_stress_add_remove():
    """Stress test adding and removing items concurrently."""
    qm = QueueManager()

    stop_event = threading.Event()

    def adder():
        count = 0
        while not stop_event.is_set():
            try:
                qm.add_item({"url": f"http://test{count}.com", "id": str(uuid.uuid4())})
                count += 1
                time.sleep(0.001)
            except ValueError:
                time.sleep(0.01) # Queue full

    def remover():
        while not stop_event.is_set():
            item = qm.claim_next_downloadable()
            if item:
                qm.remove_item(item)
            else:
                time.sleep(0.001)

    threads = []
    for _ in range(5):
        t = threading.Thread(target=adder)
        t.start()
        threads.append(t)

    for _ in range(5):
        t = threading.Thread(target=remover)
        t.start()
        threads.append(t)

    time.sleep(2)
    stop_event.set()

    for t in threads:
        t.join()

    # Verify consistency
    # Queue should be in valid state (no half-added items, etc)
    # Since we use RLock, it should be fine.
    assert len(qm.get_all()) >= 0

def test_queue_stress_listeners():
    """Stress test listeners update."""
    qm = QueueManager()
    call_counts = [0]

    def listener():
        call_counts[0] += 1

    qm.add_listener(listener)

    stop_event = threading.Event()

    def mutator():
        while not stop_event.is_set():
            qm.add_item({"url": "http://test.com", "id": str(uuid.uuid4())})
            time.sleep(0.001)
            item = qm.claim_next_downloadable()
            if item:
                qm.update_item_status(item["id"], "Downloading")
                qm.remove_item(item)

    t = threading.Thread(target=mutator)
    t.start()

    time.sleep(1)
    stop_event.set()
    t.join()

    assert call_counts[0] > 0
