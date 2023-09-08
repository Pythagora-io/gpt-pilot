from typing import List
from .detector import Detector
from .detected_config import DetectedConfig


class LanguageDetector(Detector):
    def scan_files(self, config: DetectedConfig, files: List[str]) -> None:
        if 'pom.xml' in files:
            config.language = 'Java'
        elif 'package.json' in files:
            config.language = 'TypeScript' if 'tsconfig.json' in files else 'JavaScript'
        elif 'requirements.txt' in files:
            config.language = 'Python'
