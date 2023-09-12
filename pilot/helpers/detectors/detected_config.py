from typing import Optional


class DetectedConfig:
    def __init__(self):
        self.language: Optional[str] = None
        self.repo: Optional[str] = None
        self.bugs: Optional[str] = None
        self.homepage: Optional[str] = None
