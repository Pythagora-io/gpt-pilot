from os import path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from .detector import Detector
from .detected_config import DetectedConfig
from ..files import read_json
# from ..Project import Project


class BuildDetector(Detector):
    def __init__(self, workspace: str, project):
        self.workspace = workspace
        self.project = project

    def scan_files(self, config: DetectedConfig, files: List[str]) -> None:
        if 'pom.xml' in files:
            parse_pom_xml(self.workspace, config, self.project)
        elif 'package.json' in files:
            parse_package_json(self.workspace, config, self.project)
        # TODO parse_setup_py()
        # TODO gradle, .Net etc


class PackageJsonModel:
    def __init__(self):
        self.name: Optional[str] = None
        self.repository: Optional[Dict[str, str]] = None
        self.bugs: Optional[Dict[str, str]] = None
        self.homepage: Optional[str] = None


class PomModel:
    def __init__(self):
        self.artifactId: Optional[str] = None
        self.url: Optional[str] = None
        self.scm: Optional[Dict[str, str]] = None
        self.issueManagement: Optional[Dict[str, str]] = None


def parse_package_json(workspace: str, config: DetectedConfig, project) -> None:
    pkg = read_package_json(workspace)

    if project.args['name'] is None:
        project.args['name'] = pkg['name']

    if hasattr(pkg, 'repository'):
        config.repo = pkg.repository.url

    if hasattr(pkg, 'bugs'):
        config.bugs = pkg.bugs.url

    if hasattr(pkg, 'homepage'):
        config.homepage = pkg.homepage


def parse_pom_xml(workspace: str, config: DetectedConfig, project) -> None:
    pom = read_pom_xml(workspace)

    if project.args['name'] is None:
        project.args['name'] = pom.find('./artifactId').text

    scm = pom.find('./scm/connection')
    if scm is not None:
        config.repo = scm.text

    issues = pom.find('./issueManagement/url')
    if issues is not None:
        config.bugs = issues.text

    url = pom.find('./url')
    if url is not None:
        config.homepage = url.text


def read_package_json(workspace: str, fail_if_not_exist: bool = False) -> PackageJsonModel:
    pkg = read_json(path.join(workspace, 'package.json'), fail_if_not_exist)
    # Conversion from dictionary to PackageJsonModel can be done as needed, e.g., using dataclasses or pydantic.
    return pkg


def read_pom_xml(workspace, fail_if_not_exist: bool = False):
    # return read_xml(path.join(workspace, 'pom.xml'), 'utf-8', fail_if_not_exist)
    with open(path.join(workspace, 'pom.xml'), 'r') as file:
        data = file.read()

        data = data.replace('xmlns="http://maven.apache.org/POM/4.0.0"', '')
        data = data.replace('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
        data = data.replace(
            'xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"', '')

        return ET.fromstring(data)
