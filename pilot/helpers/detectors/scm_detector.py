from .detector import Detector
from .detected_config import DetectedConfig


class ScmDetector(Detector):
    async def scan_dir(self, config: DetectedConfig, dirents):
        # if not config.repo:
        #     for dirent in dirents:
        #         if dirent.name == '.git':
        #             git_config = parse_git_config()
        #             config.repo = git_config.get('remote', {}).get('origin', {}).get('url')
        #
        #             if not config.homepage:
        #                 config.homepage = re.sub(r'^git\+(.*).git$', r'\1', config.repo or '')
        #
        #             if not config.bugs:
        #                 config.bugs = re.sub(r'^git\+(.*).git$', r'\1/issues', config.repo or '')
        #
        #             return
        pass
