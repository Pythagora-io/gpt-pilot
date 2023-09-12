from typing import List
from .detected_config import DetectedConfig


class Detector:
    def scan_dir(self, config: DetectedConfig, dirents) -> None:
        dirents = [d.name for d in dirents if d.is_file()]
        self.scan_files(config, dirents)

    def scan_files(self, config: DetectedConfig, files: List[str]) -> None:
        raise NotImplementedError('scanFiles not implemented')
