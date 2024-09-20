import concurrent
import threading
from concurrent.futures import ThreadPoolExecutor


class OCRThreadManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(OCRThreadManager, cls).__new__(cls)
                    cls._instance.executor = ThreadPoolExecutor(max_workers=5)
        return cls._instance

    def submit(self, func, *args, **kwargs):
        return self.executor.submit(func, *args, **kwargs)

    def wait(self, futures):
        concurrent.futures.wait(futures)
