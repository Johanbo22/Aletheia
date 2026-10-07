"""
Version checker module

Compares the installed application version against the latest release
on the repository on GitHub.
"""
from typing import Final, Optional

import requests
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from resources.version import APPLICATION_NAME, APPLICATION_VERSION

# Repository information
GITHUB_OWNER: Final[str] = "Johanbo22"
GITHUB_REPOSITORY: Final[str] = "Aletheia"
LATEST_RELEASE_API_URL: str = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/latest"
RELEASES_PAGE_URL: str = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPOSITORY}/releases/latest"
REQUEST_TIMEOUT_SEC: int = 10

def parse_version(version_str: str) -> tuple[int, ...]:
    """
    Parses a semantic version string into a tuple of integers

    Accepts versions with and without a leading 'v' ('v0.5.3' or '0.5.3')
    and ignores non nummeric suffixes ('0.5.3-beta')

    :param version_str: The version string to parse
    :return: A tuple of integers (0, 5, 3) matching Major, minor, patch semantics
    """
    cleaned_version: str = str(version_str).strip().lower().lstrip("v")
    numeric_parts: list[str] = []

    for part in cleaned_version.split(".")[:4]:
        digits: str = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        numeric_parts.append(digits)

    if not numeric_parts:
        raise ValueError(f"Could not parse version string: '{version_str}'")
    return tuple(int(p) for p in numeric_parts)

def normalize_latest_tag(raw_tag: str) -> str:
    """
    Strips away common prefixes from GitHub release tag names

    :param raw_tag: The raw tag_name returned by the GitHub API
    :return: A normalized release tag name
    """
    tag: str = str(raw_tag).strip()
    if tag.lower() in ("none", "null", ""):
        return "unknown"

    lowered = tag.lower()
    for prefix in ("release", "release-", "aletheia-", "aletheia", "v"):
        if lowered.startswith(prefix):
            return tag[len(prefix):].strip()
    return tag

def compare_versions(installed: str, latest: str) -> Optional[bool]:
    """
    Compares two version strings

    :param installed: The currently installed version
    :param latest: The latest release version
    :return: True if latest is newer than installed, False if they match
    """
    try:
        return parse_version(latest) > parse_version(installed)
    except ValueError:
        if normalize_latest_tag(installed).lower() == normalize_latest_tag(latest).lower():
            return False
        return None

def fetch_latest_release_tag(timeout: int = REQUEST_TIMEOUT_SEC) -> str:
    """
    Fetches the latest tag name from the GitHub API

    :param timeout: Request timeout in seconds
    :return: The latest release version tag string
    :raises requests.RequestException: On HTTP errors
    :raises ValueError: If the response cannot be decoded
    """
    headers = {
        "Accept"    : "application/vnd.github+json",
        "User-Agent": f"{APPLICATION_NAME}/{APPLICATION_VERSION}",
    }
    response = requests.get(LATEST_RELEASE_API_URL, headers=headers, timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response format from GitHub API")

    return normalize_latest_tag(payload.get("tag_name", ""))

class VersionCheckSignals(QObject):
    """
    Signals emitted by the VersionCheckWorker

    check_completed
        bool: True when a newer version is available
        str: The latest release tag
        str: The version the application is currently running
    error_object
        object: The error occured during the check
    """
    check_completed = pyqtSignal(bool, str, str)
    error_object = pyqtSignal(object)

class VersionCheckWorker(QRunnable):
    """
    Background thread to check GitHub for latest release and
    compare it against the installed application version
    """

    def __init__(self, installed_version: str = APPLICATION_VERSION) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.installed_version = installed_version
        self.signals = VersionCheckSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            latest_tag = fetch_latest_release_tag()
            update_available = compare_versions(self.installed_version, latest_tag)

            if update_available is None:
                self.signals.error_object.emit(
                    ValueError(f"Could not determine whether '{latest_tag}' is newer than '{self.installed_version}'")
                )
                return

            self.signals.check_completed.emit(update_available, latest_tag, self.installed_version)

        except Exception as err:
            self.signals.error_object.emit(err)
