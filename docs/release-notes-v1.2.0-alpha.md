# 릴리즈 노트 — v1.2.0-alpha

> **릴리즈 타입**: Pre-release (Alpha)  
> **브랜치**: `feat/deduplication-improvements`  
> **기준 커밋**: `215b212`  
> **배포 대상**: 개발자 및 고급 사용자

---

## 개요

**Phase 3 완료**: 이중 출력(Dual Output), 유연 중복 판정(Flexible Deduplication), SQLite 캐시 마이그레이션 기능이 추가되었습니다. 대용량 데이터 처리와 맞춤형 중복 판정이 가능해졌습니다.

**⚠️ 주의**: Alpha 버전으로, 프로덕션 환경보다는 테스트 및 피드백 수집 용도로 사용해 주세요.

---

## Phase 3: 이중 출력 및 고급 중복 판정

### 3.1 이중 출력 (Dual Output)

- **파일**: `src/auto_write_txt_to_docs/dual_output.py`
- **기능**: 처리된 내용을 동시에 3가지 형태로 저장
  - `output/raw/YYYY-MM-DD_raw.txt` — 중복 포함 원본
  - `output/deduped/YYYY-MM-DD_deduped.txt` — 중복 제거본
  - `output/html/YYYY-MM-DD_report.html` — 보기 좋은 HTML 리포트
- **통계**: HTML 리포트에 원본 라인 수 / 중복 제거 후 / 제거된 중복 수 카드 표시
- **활성화**: `config.json`에 `"dual_output_enabled": true` 추가

### 3.2 유연 중복 판정 (Flexible Deduplication)

- **파일**: `src/auto_write_txt_to_docs/flexible_dedup.py`
- **기능**: 특정 필드를 중복 판정에서 제외
- **설정 예시**:
  ```json
  {
    "flexible_dedup": {
      "enabled": true,
      "ignore_fields": ["time"]
    }
  }
  ```
- **효과**: 시간만 다른 동일 내용을 중복으로 처리
- **블록 모드 연동**: `StructuredBlockParser`와 함께 사용 시 더욱 강력

### 3.3 SQLite 캐시 마이그레이션

- **파일**: `src/auto_write_txt_to_docs/cache_database.py`
- **기능**: JSON 파일 기반 캐시를 SQLite로 마이그레이션
- **스키마**:
  - `line_cache` — 해시, 미리보기, 첫/마지막 발견 시간, 발생 횟수
  - `file_state` — 파일 경로, 바이트 오프셋, ctime/mtime
  - `provenance` — 해시별 출처 파일 목록
- **인덱스**: `hash`, `last_seen_at` 컬럼에 인덱스 생성
- **마이그레이션**: `migrate_from_json(cache_json, stats_json)`으로 기존 데이터 이전
- **효과**: 100,000줄 이상 대용량 캐시 안정적 처리

---

## 전체 기능 요약 (Phase 1~3)

| 기능 | Phase | 파일 | 설명 |
|---|---|---|---|
| 출처 추적 | 1 | `backend_processor.py` | 중복 라인의 발견 파일명 기록 |
| 해시 기반 캐시 | 1 | `backend_processor.py` | 메모리 36% 절약 |
| 중복 집계 API | 1 | `backend_processor.py` | TOP N 중복 라인 조회 |
| StructuredBlockParser | 2 | `block_parser.py` | 블록 단위 파싱 |
| 블록 중복 모드 | 2 | `backend_processor.py` | `content_parsing_mode: "block"` |
| 배치 최적화 | 2 | `batch_optimizer.py` | 중복률 95% 이상 시 감시 간격 조절 |
| 이중 출력 | 3 | `dual_output.py` | raw/deduped/HTML 동시 생성 |
| 유연 중복 판정 | 3 | `flexible_dedup.py` | 필드 제외 중복 판정 |
| SQLite 캐시 | 3 | `cache_database.py` | 대용량 데이터 안정적 처리 |

---

## 테스트 결과

| 테스트 모듈 | 테스트 수 | 결과 |
|---|---|---|
| `test_backend_processor.py` | 29개 | 전체 통과 |
| `test_block_parser.py` | 7개 | 전체 통과 |
| `test_batch_optimizer.py` | 5개 | 전체 통과 |
| `test_dual_output.py` | 6개 | 전체 통과 |
| `test_flexible_dedup.py` | 7개 | 전체 통과 |
| `test_cache_database.py` | 7개 | 전체 통과 |
| **합계** | **61개** | **전체 통과** |

> 프로젝트 전체 119개 테스트 중 4개 실패는 기존 환경 의존성(customtkinter 미설치 3개) 및 버전 메타데이터 이슈(1개)로 본 릴리즈와 무관합니다.

---

## 설치 및 업데이트

### 소스 실행

```powershell
git clone https://github.com/122yjs/auto_write_txt_to_docs.git
cd auto_write_txt_to_docs
git checkout feat/deduplication-improvements
pip install -r requirements.txt
python main_gui.py
```

### 설정 예시 (이중 출력 + 유연 중복 + 블록 모드)

```json
{
  "content_parsing_mode": "block",
  "block_separator": "-------------------------------------------------------------------------------",
  "field_patterns": {
    "sender": "^송신:(.+)",
    "time": "^시간:(.+)",
    "title": "^제목:(.+)",
    "body": "^내용:(.+)"
  },
  "flexible_dedup": {
    "enabled": true,
    "ignore_fields": ["time"]
  },
  "dual_output_enabled": true,
  "dual_output_dir": "C:/Users/사용자명/AppData/Roaming/MessengerDocsAutoWriter/output"
}
```

### SQLite 마이그레이션

```python
from src.auto_write_txt_to_docs.cache_database import CacheDatabase

db = CacheDatabase("cache.db")
db.migrate_from_json("added_lines_cache.json", "duplicate_stats.json")
print(f"마이그레이션 완료: {db.get_cache_size()}개 라인")
```

---

## 알려진 이슈

1. **main_gui.py와의 통합 미완료**: 블록 모드, 이중 출력, 유연 중복 설정 UI는 아직 `main_gui.py`에 추가되지 않았습니다. 설정은 `config.json` 수동 편집 또는 코드 레벨에서만 가능합니다.
2. **BatchDeduplicationOptimizer 미연동**: `run_monitoring()`에 optimizer가 정의되어 있으나, 메인 루프와의 완전한 통합은 이후 정식 릴리즈에서 진행됩니다.
3. **SQLite 선택적 사용**: 현재는 `cache_database.py`가 독립 모듈로 제공됩니다. 기존 JSON 기반 캐시와의 완전한 교체는 다음 정식 버전에서 이루어집니다.

---

## 기여 및 피드백

- 버그 리포트: [GitHub Issues](https://github.com/122yjs/auto_write_txt_to_docs/issues)
- 피드백 환영: 이중 출력 사용성, 유연 중복 필드 설정, SQLite 성능 등

---

## 다음 단계 (Roadmap)

- **v1.2.0-beta**: `main_gui.py`에 고급 설정 UI 추가 (블록 모드, 이중 출력, 유연 중복)
- **v1.2.0**: `CacheDatabase`를 기본 캐시 저장소로 전환
- **v2.0.0**: 플러그인 시스템, 크로스 플랫폼 지원

> **릴리즈일**: 2026년 5월 1일
