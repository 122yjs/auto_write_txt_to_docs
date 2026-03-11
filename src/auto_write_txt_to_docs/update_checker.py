import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src import __version__ as CURRENT_VERSION


REPOSITORY_RELEASES_URL = "https://github.com/122yjs/auto_write_txt_to_docs/releases"
LATEST_RELEASE_API_URL = "https://api.github.com/repos/122yjs/auto_write_txt_to_docs/releases/latest"


def normalize_version_tag(version_text):
    """Git 태그 문자열에서 비교 가능한 버전 문자열만 추출한다."""
    normalized = str(version_text or "").strip()
    if normalized.lower().startswith("refs/tags/"):
        normalized = normalized.split("/", 2)[-1]
    if normalized.lower().startswith("release-"):
        normalized = normalized[len("release-") :]
    if normalized[:1].lower() == "v":
        normalized = normalized[1:]
    return normalized


def parse_version_tuple(version_text):
    """버전 문자열을 숫자 튜플로 변환한다."""
    normalized = normalize_version_tag(version_text)
    number_parts = [int(part) for part in re.findall(r"\d+", normalized)]
    return tuple(number_parts)


def is_newer_version(latest_version, current_version=CURRENT_VERSION):
    """최신 버전이 현재 버전보다 높은지 판단한다."""
    latest_tuple = parse_version_tuple(latest_version)
    current_tuple = parse_version_tuple(current_version)

    max_length = max(len(latest_tuple), len(current_tuple), 1)
    padded_latest = latest_tuple + (0,) * (max_length - len(latest_tuple))
    padded_current = current_tuple + (0,) * (max_length - len(current_tuple))
    return padded_latest > padded_current


def fetch_latest_release_metadata(api_url=LATEST_RELEASE_API_URL, timeout=5):
    """GitHub 최신 릴리즈 메타데이터를 조회한다."""
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MessengerDocsAutoWriterUpdateChecker/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"업데이트 확인 API 응답 실패: HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"업데이트 확인 네트워크 오류: {error.reason}") from error

    try:
        release_data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("업데이트 확인 응답 형식이 잘못되었습니다.") from error

    if not isinstance(release_data, dict):
        raise RuntimeError("업데이트 확인 응답 형식이 올바르지 않습니다.")

    return release_data


def check_for_new_release(
    current_version=CURRENT_VERSION,
    api_url=LATEST_RELEASE_API_URL,
    timeout=5,
):
    """현재 버전 대비 최신 릴리즈 정보를 반환한다."""
    release_data = fetch_latest_release_metadata(api_url=api_url, timeout=timeout)
    latest_version = normalize_version_tag(release_data.get("tag_name"))
    current_version_text = normalize_version_tag(current_version)

    if not latest_version:
        raise RuntimeError("최신 릴리즈 태그를 확인할 수 없습니다.")

    return {
        "current_version": current_version_text,
        "latest_version": latest_version,
        "update_available": is_newer_version(latest_version, current_version=current_version_text),
        "release_name": str(release_data.get("name") or "").strip(),
        "release_url": str(release_data.get("html_url") or REPOSITORY_RELEASES_URL).strip(),
        "published_at": str(release_data.get("published_at") or "").strip(),
        "tag_name": str(release_data.get("tag_name") or "").strip(),
    }
