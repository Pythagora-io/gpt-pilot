import os
# from ..Project import Project
from .build_detector import BuildDetector
from .language_detector import LanguageDetector
from .detected_config import DetectedConfig


def run_detectors(project) -> DetectedConfig:
    config = DetectedConfig()
    workspace = project.args['workspace'] if 'workspace' in project.args else None

    if workspace is not None:
        # TODO can/should ask_user accept a default project name inferred from the directory name?
        # if project.args['name'] is None:
        #     project.args['name'] = os.path.basename(workspace)

        detectors = [
            BuildDetector(workspace, project),
            LanguageDetector(),
            # ScmDetector(),
        ]

        for detector in detectors:
            files = os.scandir(workspace)
            detector.scan_dir(config, files)

    return config
