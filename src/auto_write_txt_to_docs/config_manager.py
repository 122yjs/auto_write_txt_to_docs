import json
from datetime import datetime
from pathlib import Path

from src.auto_write_txt_to_docs.path_utils import CONFIG_FILE_STR, LEGACY_CONFIG_FILE_STR


CONFIG_DEFAULTS = {
    "first_run": True,
    "launch_on_windows_startup": False,
    "watch_folder": "",
    "docs_input": "",
    "show_help_on_startup": True,
    "show_success_notifications": True,
    "file_extensions": ".txt",
    "use_regex_filter": False,
    "regex_pattern": "",
    "appearance_mode": "System",
    "max_cache_size": 10000,
}

BACKUP_VERSION = "1.0"


def get_default_config():
    """기본 설정값 사본을 반환한다."""
    return dict(CONFIG_DEFAULTS)


def normalize_config_data(config_data):
    """알려진 설정 키만 유지하고 누락 키는 기본값으로 채운다."""
    normalized_config = get_default_config()
    if isinstance(config_data, dict):
        for key in normalized_config:
            if key in config_data:
                normalized_config[key] = config_data[key]

    try:
        max_cache_size = int(str(normalized_config["max_cache_size"]).strip())
        if max_cache_size <= 0:
            raise ValueError
        normalized_config["max_cache_size"] = max_cache_size
    except (TypeError, ValueError):
        normalized_config["max_cache_size"] = CONFIG_DEFAULTS["max_cache_size"]

    return normalized_config


def resolve_config_path(config_path=CONFIG_FILE_STR, legacy_config_path=LEGACY_CONFIG_FILE_STR):
    """현재 설정 파일이 없으면 레거시 경로를 우선적으로 선택한다."""
    config_file = Path(config_path)
    legacy_file = Path(legacy_config_path)

    if config_file.exists():
        return config_file, False

    if legacy_file != config_file and legacy_file.exists():
        return legacy_file, True

    return config_file, False


def load_app_config(config_path=CONFIG_FILE_STR, legacy_config_path=LEGACY_CONFIG_FILE_STR):
    """앱 설정을 읽고, 실제로 사용한 경로와 레거시 여부를 함께 반환한다."""
    resolved_path, loaded_from_legacy = resolve_config_path(config_path, legacy_config_path)

    if not resolved_path.exists():
        return get_default_config(), str(resolved_path), loaded_from_legacy, False

    with resolved_path.open("r", encoding="utf-8") as config_file:
        config_data = json.load(config_file)

    normalized_config = normalize_config_data(config_data)
    if isinstance(config_data, dict) and config_data and "first_run" not in config_data:
        normalized_config["first_run"] = False

    return normalized_config, str(resolved_path), loaded_from_legacy, True


def save_app_config(config_data, config_path=CONFIG_FILE_STR):
    """정규화된 앱 설정을 지정한 경로에 저장한다."""
    normalized_config = normalize_config_data(config_data)
    target_path = Path(config_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as config_file:
        json.dump(normalized_config, config_file, indent=4, ensure_ascii=False)

    return normalized_config


def build_backup_payload(config_data, backup_time=None):
    """백업 파일에 저장할 설정과 메타데이터를 구성한다."""
    normalized_config = normalize_config_data(config_data)
    timestamp = backup_time or datetime.now()

    backup_payload = dict(normalized_config)
    backup_payload["backup_date"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    backup_payload["backup_version"] = BACKUP_VERSION
    return backup_payload


def save_backup_config(backup_path, config_data, backup_time=None):
    """백업 파일을 저장하고 실제 저장한 데이터를 반환한다."""
    target_path = Path(backup_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    backup_payload = build_backup_payload(config_data, backup_time=backup_time)

    with target_path.open("w", encoding="utf-8") as backup_file:
        json.dump(backup_payload, backup_file, indent=4, ensure_ascii=False)

    return backup_payload


def load_backup_config(backup_path):
    """백업 파일을 읽고 복원용 설정과 원본 메타데이터를 함께 반환한다."""
    backup_file = Path(backup_path)

    with backup_file.open("r", encoding="utf-8") as source_file:
        backup_data = json.load(source_file)

    normalized_config = normalize_config_data(backup_data)
    if isinstance(backup_data, dict) and backup_data and "first_run" not in backup_data:
        normalized_config["first_run"] = False

    return normalized_config, backup_data
