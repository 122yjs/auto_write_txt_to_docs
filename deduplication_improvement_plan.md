# 중복 감지 로직 비교 분석 및 개선 계획

> **작성 목적**: 현재 프로젝트(`auto_write_txt_to_docs`)의 중복 감지 로직과 EzQ 쪽지 백업 문서의 중복 제거 설계를 비교하고, 양쪽의 장점을 혼합한 개선안을 수립  
> **근거 문서**: `src/auto_write_txt_to_docs/backend_processor.py`, `EZQ_Dedup_Workflow.md`  
> **작성 시점**: v1.0.4 기준  

---

## 1. 현재 프로젝트 중복 감지 방식

### 1.1 핵심 아키텍처

현재 프로젝트는 **실시간 파일 감시 + 증분 처리**를 기반으로, **라인(Line) 단위**로 중복을 판정합니다.

```
[파일 감지] → [바이트 오프셋 읽기] → [라인 분할] → [중복 필터] → [Google Docs 기록]
```

#### 1.1.1 이중 캐시 구조

| 캐시 | 자료구조 | 목적 | 영속성 |
|---|---|---|---|
| **전역 라인 캐시** | `OrderedDict[str, None]` | 모든 파일에서 이미 기록한 라인 문자열 저장 | `added_lines_cache.json` |
| **파일별 해시 세트** | `dict[filepath, set[str]]` | 파일별로 이미 처리한 라인의 SHA256 해시 저장 | `processed_state.json` |

#### 1.1.2 중복 판정 로직 (L773-780)

```python
# backend_processor.py
import hashlib

def hash_line_for_dedupe(line):
    return hashlib.sha256(line.encode('utf-8')).hexdigest()

truly_new_lines = [
    line for line in new_lines
    if line not in added_lines_cache           # 전역 캐시에 없고
    and hash_line_for_dedupe(line) not in file_seen_hashes  # 파일별 해시에도 없으면
]
```

- **전역 캐시 hit**: 파일 이름과 무관하게, 이미 어떤 파일에서든 기록한 라인은 중복
- **파일별 해시 hit**: 동일 파일에서 이전에 처리한 라인은 중복 (파일 재생성 시 초기화)
- **둘 다 miss**: 새로운 라인으로 판정, Google Docs에 기록

#### 1.1.3 증분 처리 메커니즘

| 상태 | 동작 |
|---|---|
| `current_byte_size > last_byte_offset` | 오프셋부터 새 내용만 읽음 |
| `current_byte_size < last_byte_offset` | 파일 크기 감소로 간주, 전체 재읽기 |
| `ctime 변경` 또는 `created 이벤트` | 파일 재생성으로 간주, 해시 세트 초기화 |
| `1초 내 재처리` | `PROCESSING_DELAY=1.0`로 중복 이벤트 무시 |

#### 1.1.4 LRU-like 캐시 관리

```python
# MAX_GLOBAL_CACHE_SIZE = 10,000 (기본)
def optimize_cache_size(log_func):
    items_to_remove = len(added_lines_cache) - MAX_GLOBAL_CACHE_SIZE
    if items_to_remove > 0:
        for _ in range(items_to_remove):
            added_lines_cache.popitem(last=False)  # 가장 오래된 항목 제거
```

- **장점**: 메모리 사용량 상한 보장
- **한계**: 10,001번째 고유 라인부터는 1번째 라인이 캐시에서 제거되어, 나중에 동일 라인이 재등장하면 "새 라인"으로 오인

#### 1.1.5 전체 중복 시나리오 처리

```python
if not truly_new_lines:  # 전부 중복
    if should_record_duplicate_file_marker:  # 처음 처리되는 파일
        # Google Docs에 "# 중복 파일: {파일명}"만 기록
        duplicate_record = build_duplicate_only_record(filepath, duplicate_line_count)
    else:
        # 아무 것도 하지 않음
        log_func(f"중복 내용만 감지되어 Google Docs 기록 생략")

# 중복이어도 캐시에 기록 (다음번 중복 방지용)
remember_global_lines(new_lines)
remember_file_lines(filepath, new_lines)
```

#### 1.1.6 UI 연동 및 설정

**설정 파일 연동** (`config_manager.py` L21):
```python
CONFIG_DEFAULTS = {
    # ...
    "max_cache_size": 10000,  # 기본값
}
```

**UI 입력 필드** (`main_window_ui.py` L489–562):
- "라인 캐시 크기" 입력 필드 제공
- 사용자가 `max_cache_size`를 직접 수정 가능
- 숫자 외 입력 시 `parse_max_cache_size()`로 검증

**메인 GUI 바인딩** (`main_gui.py` L517):
```python
self.max_cache_size_var = tk.StringVar(value=str(config.get('max_cache_size', 10000)))
```
- 설정 변경 시 `trace_add("write")`로 `settings_changed` 플래그 갱신
- 저장 시 `configure_max_global_cache_size(config)` 호출

**중복 알림 UI** (`result_popup.py` L49–55):
```python
LEVEL_STYLE = {
    "duplicate": {
        "accent": ("#F59E0B", "#D97706"),  # 노란색/주황색 악센트
        "title": "중복 알림",
    },
    # ...
}
```
- 중복 파일 처리 시 우하단 팝업에 노란색 악센트 바 표시
- 파일명 + 중복 줄 수 + 미리보기 2줄 포함

#### 1.1.7 테스트 커버리지

`tests/test_backend_processor.py`에서 중복 감지 관련 테스트:

| 테스트 영역 | 라인 범위 | 내용 |
|---|---|---|
| **기본 중복 필터** | L168–217 | 동일 라인 2회 입력 시 2회째 중복으로 판정, Google Docs 기록 생략 확인 |
| **전역 캐시 동작** | L327–407 | `added_lines_cache` 로드/저장, `optimize_cache_size()` 호출 시 오래된 항목 제거, 10,001번째 라인 입력 시 1번째 라인 eviction 확인 |
| **파일별 해시 세트** | L463–498 | `remember_file_lines()` + `get_file_seen_hashes()` 동작, 파일 재생성 시 `reset_file_processing_state()`로 해시 세트 초기화 확인 |

**테스트 커버리지 현황**:
- 전역 캐시: **커버됨** (LRU eviction, JSON 직렬화/역직렬화)
- 파일별 해시: **커버됨** (SHA-256 해시 생성, set 동작, 초기화)
- 중복 판정 AND 조건: **부분 커버** (전역 캐시 miss + 파일별 miss 시나리오는 있으나, "전역 hit + 파일별 miss" 또는 "전역 miss + 파일별 hit" 분기별 테스트는 명시되지 않음)
- `should_record_duplicate_file_marker`: **미커버** (brand-new 파일 전체 중복 시 파일명 기록 시나리오 테스트 없음)
- 출처 추적(Provenance): **미커버** (현재 기능 없음)

#### 1.1.8 레거시 버전과의 차이

`backup/backend_processor.py` (초기 버전)과 현재 버전 비교:

| 항목 | 레거시 (`backup/`) | 현재 (`src/`) |
|---|---|---|
| **전역 캐시** | `set()` (무제한) | `OrderedDict()` (LRU, 10,000개 제한) |
| **해시 알고리즘** | 없음 (라인 문자열 직접 비교) | SHA-256 |
| **파일별 상태** | `size`, `timestamp`만 저장 | `last_byte_offset`, `seen_line_hashes`, `file_ctime_ns` 등 다양 |
| **파일 재생성 감지** | 없음 | `ctime_changed` 감지 + 자동 초기화 |
| **영속성** | `added_lines_cache.json`만 | `added_lines_cache.json` + `processed_state.json` |
| **재시도 메커니즘** | 없음 | `schedule_retry()` + `threading.Timer` |
| **인코딩 처리** | 없음 | UTF-8, CP949, EUC-KR 자동 감지 |

**마이그레이션 히스토리**:
- `set()` → `OrderedDict`: 메모리 무제한 증가 방지
- 라인 문자열 직접 비교 → SHA-256: 파일별 상태 직렬화 시 효율성 향상 (64자 hex 문자열 vs 가변 길이 라인)
- 단일 캐시 → 이중 캐시(전역 + 파일별): 파일 재생성 시에도 정확한 중복 판정 가능

---

## 2. EzQ 쪽지 백업 중복 제거 설계

### 2.1 핵심 아키텍처

EzQ 설계는 **일괄 배치 처리**를 기반으로, **쪽지(Note) 단위**로 중복을 판정합니다.

```
[백업 TXT 파일 읽기] → [구분선 기준 블록 분할] → [메타데이터 추출] → [지문 생성] → [중복 필터] → [저장소 기록]
```

#### 2.1.1 블록 파싱 및 메타데이터 추출

```text
송신:이슬아
시간:2026-03-18 13:04:58:000
제목:그럼 그날 1교시를 6교시로.. 감사합니다!
내용:그럼 그날 1교시를 6교시로.. 감사합니다!
-------------------------------------------------------------------------------
```

- 구분선(`-` 반복)으로 블록 분할
- 각 블록에서 `송신`, `시간`, `제목`, `내용` 필드 추출
- 필드가 4개 모두 있으면 "쪽지 한 건"으로 인정

#### 2.1.2 쪽지 지문 (Fingerprint)

```python
# 의사 코드
fingerprint_input = f"{쪽지함_종류}\n{병은_사람}\n{병은_시간}\n{제목}\n{내용}"
fingerprint = hashlib.sha256(fingerprint_input.encode('utf-8')).hexdigest()
```

- **쪽지함 종류 포함**: `받은쪽지함`과 `병은쪽지함`은 다른 쪽지로 처리
- **시간 포함**: 같은 내용이라도 시간이 다륾 다른 쪽지
- **병은 사람 포함**: 같은 내용이라도 병은 사람이 다륾 다른 쪽지

#### 2.1.3 이중 저장소 구조

| 저장소 | 역할 | 스키마 예시 |
|---|---|---|
| **쪽지 목록** | 중복 제거된 쪽지 본문 저장 | `fingerprint, 쪽지함, 송신, 시간, 제목, 내용` |
| **출처 목록** | 쪽지 발견 파일명 기록 | `fingerprint, 파일명` |

#### 2.1.4 중복 판정 로직

```python
# 의사 코드
if fingerprint not in saved_fingerprints:
    save_note(note)           # 쪽지 목록에 추가
    saved_fingerprints.add(fingerprint)

save_source(fingerprint, backup_file)  # 출처 목록에는 항상 추가
```

- **중복이면**: 쪽지 목록에 추가하지 않음, 출처 목록에만 파일명 누적
- **새 쪽지면**: 쪽지 목록 + 출처 목록 모두 추가

#### 2.1.5 페이지 순회 최적화

```python
page_fingerprints = make_fingerprints(page_notes)
if all(f in saved_fingerprints for f in page_fingerprints):
    stop_page_loop()  # 현재 페이지 전부 중복 → 이전에 백업했을 가능성 높음 → 중단
```

- **장점**: 불필요한 페이지 순회 방지, 처리 시간 단축
- **한계**: 안전을 위해 "한 페이지 더 확인" 옵션 필요

#### 2.1.6 출력 파일 구조

| 파일 | 내용 | 중복 처리 |
|---|---|---|
| `notes_raw.csv` | 원본 그대로 | 중복 포함 (원본 검증용) |
| `notes.csv` | 중복 제거된 쪽지 | `duplicate_count`, `source_names` 포함 |
| `notes.html` | 사람이 보기 좋은 형태 | 받은/병은 구분, 반복 파일 목록 표시 |

---

## 3. 비교 분석

### 3.1 기능적 비교

| 항목 | 현재 프로젝트 | EzQ 설계 | 비고 |
|---|---|---|---|
| **처리 방식** | 실시간 증분 (스트리밍) | 일괄 배치 (Batch) | 용도가 다름 |
| **중복 단위** | 라인 (Line) | 쪽지/블록 (Block) | 의미 단위 vs 텍스트 단위 |
| **해시 기준** | 라인 문자열 전체 SHA256 | 쪽지함+송신+시간+제목+내용 SHA256 | EzQ가 의미 기반 |
| **메타데이터 활용** | 없음 (라인 문자엧만) | 있음 (송신, 시간, 제목, 내용 분리) | EzQ가 구조화 |
| **출처 추적** | 없음 | 있음 (발견 파일명 목록) | EzQ가 데이터 계보 관리 |
| **중복 집계** | 카운트만 (N줄 중복) | 횟수 + 파일 목록 | EzQ가 상세 |
| **페이지/배치 중단** | 없음 | 있음 (전체 중복 시 중단) | EzQ가 효율적 |
| **캐시 구조** | OrderedDict (LRU-like, 10,000개) | 전역 지문 세트 | 현재 프로젝트가 메모리 최적화 |
| **영속성** | JSON 2개 파일 | CSV 3개 파일 | 현재 프로젝트가 경량 |
| **파일 재생성 대응** | ctime/mtime 감지 → 자동 초기화 | 없음 (일괄 처리) | 현재 프로젝트가 견고 |
| **인코딩 처리** | UTF-8, CP949, EUC-KR 자동 감지 | 명시되지 않음 | 현재 프로젝트가 다국어 지원 |
| **이중 출력** | 없음 (Google Docs만) | 있음 (raw/deduped/html) | EzQ가 유연 |
| **용도 적합성** | 실시간 메신저 로그 수집 | EzQ 쪽지 백업 통합 | 각자의 도메인에 최적 |

### 3.2 강점 및 약점

#### 현재 프로젝트의 강점
1. **실시간 증분 처리**: 바이트 오프셋으로 새 내용만 읽어 효율적
2. **파일 재생성 감지**: ctime 변경 감지로 안정적 초기화
3. **이중 중복 방지**: 전역 캐시 + 파일별 해시로 높은 정확도
4. **메모리 상한 관리**: LRU-like 캐시로 메모리 누수 방지
5. **다중 인코딩**: 한국어 환경에 최적화된 인코딩 감지
6. **자동 재시도**: Google Docs 실패 시 5초 후 재시도

#### 현재 프로젝트의 약점
1. **라인 단위 중복**: "쪽지"나 "문단" 같은 의미 단위가 아닌, 단순 텍스트 라인으로 판정
2. **출처 추적 부재**: 중복이어도 어느 파일에서 발견됐는지 기록하지 않음
3. **메타데이터 무시**: 파일 내 메타데이터(보낸 사람, 시간 등)를 활용하지 않음
4. **캐시 한계**: 10,000줄 초과 시 오래된 라인이 캐시에서 제거되어 오인 가능
5. **이중 출력 없음**: 원본(중복 포함)과 중복 제거본을 동시에 남기지 않음
6. **블록 단위 처리 불가**: `---` 구분선 기준 블록을 하나의 단위로 처리할 수 없음

#### EzQ 설계의 강점
1. **의미 단위 중복**: "쪽지"라는 도메인 단위로 중복 판정
2. **출처 추적 (Provenance)**: 데이터 계보(Lineage) 관리
3. **메타데이터 분리**: 송신, 시간, 제목, 내용을 필드별로 분리
4. **중복 집계**: `duplicate_count`와 `source_names`로 통계 제공
5. **페이지 중단**: 전체 중복 시 순회 중단으로 효율성 향상
6. **이중 출력**: raw/deduped/html 3가지 형태 동시 생성

#### EzQ 설계의 약점
1. **실시간 처리 불가**: 일괄 배치 방식이라 실시간 감시에 부적합
2. **증분 처리 없음**: 전체 파일을 매번 읽어야 함
3. **파일 재생성 대응 없음**: 파일이 교체되어도 구분 불가
4. **인코딩 처리 미흡**: 한국어 인코딩 자동 감지 로직 없음
5. **메모리 관리 없음**: 모든 지문을 메모리에 유지 (대용량 시 위험)
6. **Google Docs 연동 없음**: 출력이 로컬 파일에만 한정

---

## 4. 개선 계획 (혼합안)

> **방향성**: 현재 프로젝트의 **실시간 증분 처리**와 **파일 재생성 감지**를 유지하면서, EzQ의 **의미 단위 중복**, **출처 추적**, **메타데이터 분리**, **이중 출력**을 도입합니다.

---

### Phase 1: 단기 (2~3주) — 출처 추적 및 해시 기반 캐시 개선

#### 1.1 [P1] 출처 추적 (Provenance Tracking) 도입

**목표**: 중복이어도 어느 파일에서 발견됐는지 기록하여 데이터 계보 관리

**현재 상태**:
```python
# processed_state.json
{
  "C:/logs/chat.txt": {
    "last_byte_offset": 1024,
    "seen_line_hashes": ["abc123", "def456"],
    "file_ctime_ns": 1234567890000
  }
}
```

**개선 방안**:
```python
# processed_state.json
{
  "C:/logs/chat.txt": {
    "last_byte_offset": 1024,
    "seen_line_hashes": ["abc123", "def456"],
    "file_ctime_ns": 1234567890000,
    "provenance": {  # ← 신규
      "abc123": ["chat-2026-03-18_130726.txt", "chat-2026-03-18_134821.txt"],
      "def456": ["chat-2026-03-18_130740.txt"]
    }
  }
}
```

**구현**:
```python
# backend_processor.py - remember_file_lines 개선
def remember_file_lines(filepath, lines, source_filename=None):
    """현재 파일에서 확인한 라인들을 파일별 중복 상태에 기록. 출처도 함께 기록."""
    if not lines:
        return

    source = source_filename or os.path.basename(filepath)
    with processed_state_lock:
        state = get_file_state(filepath)
        seen_hashes = get_file_seen_hashes(filepath)
        provenance = state.setdefault('provenance', {})

        for line in lines:
            h = hash_line_for_dedupe(line)
            seen_hashes.add(h)
            if h not in provenance:
                provenance[h] = []
            if source not in provenance[h]:
                provenance[h].append(source)
```

**기대 효과**:
- 중복 라인이어도 "이 라인은 fileA, fileB에서도 발견됨" 로깅 가능
- 문제 발생 시 원본 파일 추적 용이
- Google Docs 중복 파일명 기록 시, 발견 파일 목록 포함 가능

---

#### 1.2 [P2] 해시 기반 전역 캐시 개선 (메모리 최적화)

**목표**: 현재 라인 문자열을 키로 사용하는 캐시를 해시값 기반으로 변경하여 메모리 절약

**현재 상태**:
```python
added_lines_cache = OrderedDict()
# 키: 라인 문자열 전체 (예: "이슬아: 감사합니다!" → 20~100바이트)
# 값: None
```

**개선 방안**:
```python
added_lines_cache = OrderedDict()
# 키: SHA256 해시 (32바이트 고정, 64문자 hex)
# 값: 원본 라인 문자열 (필요시 조회용, None 가능)
```

**구현**:
```python
def remember_global_lines(lines):
    """해시값만을 키로 사용하는 전역 라인 캐시에 기록."""
    if not lines:
        return

    for line in lines:
        h = hash_line_for_dedupe(line)
        if h in added_lines_cache:
            added_lines_cache.move_to_end(h)
        else:
            added_lines_cache[h] = line  # 해시 → 원본 매핑 (조회용)

    optimize_cache_size(None)

def is_line_duplicate(line):
    """라인이 전역 캐시에 있는지 해시 기반으로 확인."""
    return hash_line_for_dedupe(line) in added_lines_cache
```

**메모리 절약 효과**:
- 기존: 라인 평균 50바이트 × 10,000줄 = 500KB (키만)
- 개선: 32바이트 × 10,000줄 = 320KB (키만, 36% 절약)
- 실제: 라인이 길수록(100~500바이트) 절약 효과 증가

---

#### 1.3 [P3] 중복 집계 및 통계 기록

**목표**: `duplicate_stats`를 도입하여 라인별/파일별 중복 횟수 집계

**구현**:
```python
# processed_state.json
{
  "duplicate_stats": {
    "abc123": {
      "line_preview": "이슬아: 감사합니다!",
      "total_occurrences": 7,
      "first_seen_at": "2026-03-18T13:04:58",
      "source_files": [
        "chat-2026-03-18_130726.txt",
        "chat-2026-03-18_130740.txt",
        "chat-2026-03-18_134821.txt"
      ]
    }
  }
}
```

**UI 연동**:
- "중복 통계" 탭 추가
- "가장 많이 중복된 라인 TOP 10" 표시
- "이 라인은 N개 파일에서 M번 중복됨" 카드 표시

---

### Phase 2: 중기 (4~6주) — 구조화된 콘텐츠 파싱 및 블록 단위 중복

#### 2.1 [P4] 구조화된 콘텐츠 파싱 모드 (Structured Content Parsing)

**목표**: 단순 라인 단위가 아닌, EzQ처럼 "블록 + 메타데이터" 단위로 파싱할 수 있는 모드 추가

**사용 시나리오**:
- 메신저 백업 파일: `송신:`, `시간:`, `제목:`, `내용:` 필드가 있는 파일
- 로그 파일: `timestamp [level] message` 패턴이 있는 파일
- CSV/TSV 파일: 컬럼 단위로 메타데이터 분리

**설정 UI 추가**:
```json
{
  "content_parsing_mode": "structured",
  "block_separator": "-------------------------------------------------------------------------------",
  "field_patterns": {
    "sender": "^송신:(.+)",
    "timestamp": "^시간:(.+)",
    "title": "^제목:(.+)",
    "body": "^내용:(.+)"
  }
}
```

**구현**:
```python
# backend_processor.py - StructuredBlockParser
import re
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class StructuredBlock:
    sender: Optional[str]
    timestamp: Optional[str]
    title: Optional[str]
    body: str
    raw_text: str
    source_file: str

class StructuredBlockParser:
    def __init__(self, config):
        self.separator = config.get('block_separator', '---')
        self.field_patterns = config.get('field_patterns', {})
        self.compiled_patterns = {
            k: re.compile(v) for k, v in self.field_patterns.items()
        }

    def parse(self, content: str, source_file: str) -> List[StructuredBlock]:
        blocks = []
        raw_blocks = content.split(self.separator)

        for raw_block in raw_blocks:
            lines = [line.strip() for line in raw_block.strip().split('\n') if line.strip()]
            if not lines:
                continue

            fields = {'body': '\n'.join(lines)}
            for field_name, pattern in self.compiled_patterns.items():
                for line in lines:
                    match = pattern.match(line)
                    if match:
                        fields[field_name] = match.group(1).strip()
                        break

            blocks.append(StructuredBlock(
                sender=fields.get('sender'),
                timestamp=fields.get('timestamp'),
                title=fields.get('title'),
                body=fields.get('body', ''),
                raw_text=raw_block.strip(),
                source_file=source_file
            ))

        return blocks
```

**중복 판정**:
```python
def compute_block_fingerprint(block: StructuredBlock, context: str = "") -> str:
    """StructuredBlock의 지문을 생성."""
    fingerprint_input = f"{context}\n{block.sender or ''}\n{block.timestamp or ''}\n{block.title or ''}\n{block.body}"
    return hashlib.sha256(fingerprint_input.encode('utf-8')).hexdigest()
```

**기대 효과**:
- "감사합니다"라는 라인이 여러 쪽지에 등장해도, 전체 쪽지가 다륾 다른 쪽지로 처리
- 메타데이터(보낸 사람, 시간) 활용으로 더 정확한 중복 판정

---

#### 2.2 [P5] 블록 단위 중복 판정 모드 (Block-Level Deduplication)

**목표**: 사용자 설정으로 "블록 단위 중복 판정" 추가

**동작 방식**:
```python
# 기존 모드 (라인 단위)
new_lines = [line for line in lines if not is_duplicate(line)]

# 블록 모드 (신규)
blocks = parse_blocks(content)
new_blocks = [block for block in blocks if not is_block_duplicate(block)]
```

**블록 중복 판정 기준**:
```python
def is_block_duplicate(block: StructuredBlock) -> bool:
    fp = compute_block_fingerprint(block)
    return fp in global_block_cache or fp in file_block_cache
```

**Google Docs 기록 형태**:
```text
# 블록 단위 기록 시
## [받은쪽지함] 이슬아 (2026-03-18 13:04:58)
**제목**: 그럼 그날 1교시를 6교시로.. 감사합니다!
**내용**: 그럼 그날 1교시를 6교시로.. 감사합니다!

## [보낸쪽지함] 김민정 (2026-03-18 13:10:22)
**제목**: 확인했습니다
**내용**: 확인했습니다
```

---

#### 2.3 [P6] 페이지/배치 중단 최적화

**목표**: EzQ의 "페이지 전체 중복 시 순회 중단" 아이디어를 실시간 감시에 적용

**구현**:
```python
# 배치 단위 중복 감지
class BatchDeduplicationOptimizer:
    def __init__(self, threshold=0.95):
        self.threshold = threshold  # 95% 중복 시 배치 중단
        self.batch_stats = {}

    def analyze_batch(self, filepaths: List[str]) -> bool:
        """배치 내 파일들의 중복률 분석."""
        total_lines = 0
        duplicate_lines = 0

        for filepath in filepaths:
            lines = read_file_lines(filepath)
            total_lines += len(lines)
            duplicate_lines += sum(1 for line in lines if is_duplicate(line))

        if total_lines == 0:
            return False

        duplicate_ratio = duplicate_lines / total_lines
        return duplicate_ratio >= self.threshold

    def should_increase_watch_interval(self, watch_folder: str) -> bool:
        """감시 폴더의 최근 배치가 전부 중복이면 감시 간격 증가."""
        recent_files = get_recent_files(watch_folder, limit=10)
        if self.analyze_batch(recent_files):
            return True
        return False
```

**감시 간격 동적 조절**:
```python
if optimizer.should_increase_watch_interval(watch_folder):
    # 1초 → 5초 → 10초 → 30초 → 60초
    new_interval = min(current_interval * 2, 60)
    log_func(f"최근 배치 전부 중복. 감시 간격을 {new_interval}초로 조정합니다.")
```

---

### Phase 3: 장기 (6~8주) — 이중 출력 및 메타데이터 기반 중복

#### 3.1 [P7] 이중 출력 지원 (Dual Output)

**목표**: EzQ의 `notes_raw.csv` + `notes.csv` + `notes.html`처럼, 중복 포함 원본과 중복 제거본을 동시에 생성

**출력 구조**:
```
%APPDATA%\MessengerDocsAutoWriter\output\
├── raw\              # 중복 포함 원본 (Google Docs 외 추가 저장)
│   └── YYYY-MM-DD_raw.txt
├── deduped\          # 중복 제거본
│   └── YYYY-MM-DD_deduped.txt
└── html\             # 보기 좋은 형태
    └── YYYY-MM-DD_report.html
```

**구현**:
```python
class DualOutputManager:
    def __init__(self, output_dir):
        self.raw_dir = os.path.join(output_dir, 'raw')
        self.deduped_dir = os.path.join(output_dir, 'deduped')
        self.html_dir = os.path.join(output_dir, 'html')
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.deduped_dir, exist_ok=True)
        os.makedirs(self.html_dir, exist_ok=True)

    def write_raw(self, filepath, lines):
        """중복 포함 원본 저장."""
        with open(self._raw_path(), 'a', encoding='utf-8') as f:
            f.write(f"\n# 파일: {os.path.basename(filepath)}\n")
            f.write('\n'.join(lines) + '\n')

    def write_deduped(self, filepath, lines, duplicate_count):
        """중복 제거본 저장."""
        with open(self._deduped_path(), 'a', encoding='utf-8') as f:
            f.write(f"\n# 파일: {os.path.basename(filepath)} (중복 {duplicate_count}줄 제거)\n")
            f.write('\n'.join(lines) + '\n')

    def generate_html(self, date_str):
        """HTML 리포트 생성."""
        # ... HTML 템플릿 렌더링
        pass
```

---

#### 3.2 [P8] 메타데이터 기반 유연 중복 판정

**목표**: 현재의 "완전 일치" 중복 판정에서, 메타데이터를 활용한 유연한 중복 판정 추가

**사용 시나리오**:
```text
# 파일 A
송신:이슬아
시간:2026-03-18 13:04:58:000
제목:감사합니다
내용:감사합니다

# 파일 B
송신:이슬아
시간:2026-03-18 13:10:22:000
제목:감사합니다
내용:감사합니다
```

- 현재: 시간이 다륾 완전히 다른 라인 → 둘 다 기록
- 개선 옵션: "시간 제외 중복 판정" → 시간만 다르고 나머지가 같으면 중복으로 처리

**구현**:
```python
class FlexibleDeduplicationStrategy:
    def __init__(self, config):
        self.ignore_fields = config.get('ignore_fields_for_dedup', [])
        # 예: ["timestamp"], ["sender", "timestamp"]

    def compute_fingerprint(self, block: StructuredBlock) -> str:
        fields = {
            'sender': block.sender,
            'timestamp': block.timestamp,
            'title': block.title,
            'body': block.body
        }
        for field in self.ignore_fields:
            fields.pop(field, None)

        fingerprint_input = '\n'.join(str(v) for v in fields.values() if v)
        return hashlib.sha256(fingerprint_input.encode('utf-8')).hexdigest()
```

**설정 UI**:
```json
{
  "flexible_dedup": {
    "enabled": true,
    "ignore_fields": ["timestamp"]
  }
}
```

---

#### 3.3 [P9] 캐시 지속성 개선 (SQLite 마이그레이션)

**목표**: 현재 JSON 파일 기반 캐시를 SQLite로 마이그레이션하여 대용량 데이터 처리

**이유**:
- `added_lines_cache.json`: 10,000줄 이상 시 파일 크기 증가, 로드/저장 지연
- `processed_state.json`: 파일 수 증가 시 메모리 사용량 증가

**SQLite 스키마**:
```sql
CREATE TABLE line_cache (
    hash TEXT PRIMARY KEY,
    line_preview TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1
);

CREATE TABLE file_state (
    filepath TEXT PRIMARY KEY,
    last_byte_offset INTEGER,
    file_ctime_ns INTEGER,
    file_mtime_ns INTEGER,
    last_attempt_time REAL
);

CREATE TABLE provenance (
    hash TEXT,
    source_file TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hash, source_file)
);

CREATE INDEX idx_line_cache_last_seen ON line_cache(last_seen_at);
CREATE INDEX idx_provenance_hash ON provenance(hash);
```

**ORM wrapper**:
```python
import sqlite3
from contextlib import contextmanager

class CacheDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def is_duplicate(self, line_hash: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("SELECT 1 FROM line_cache WHERE hash = ?", (line_hash,))
            return cursor.fetchone() is not None

    def add_line(self, line_hash: str, line_preview: str):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO line_cache (hash, line_preview) VALUES (?, ?)
                   ON CONFLICT(hash) DO UPDATE SET
                   last_seen_at = CURRENT_TIMESTAMP,
                   occurrence_count = occurrence_count + 1""",
                (line_hash, line_preview)
            )

    def get_duplicate_stats(self, limit: int = 10):
        with self._connect() as conn:
            cursor = conn.execute(
                """SELECT hash, line_preview, occurrence_count
                   FROM line_cache ORDER BY occurrence_count DESC LIMIT ?""",
                (limit,)
            )
            return cursor.fetchall()
```

**기대 효과**:
- 100,000줄 이상 캐시도 안정적 처리
- `O(1)` 해시 조회 유지 (SQLite 인덱스)
- 캐시 크기 제한 없이 전체 히스토리 유지 가능
- 통계 쿼리 용이 (TOP N 중복 라인 등)

---

## 5. 구현 로드맵

```
2024년
├── 2월 (Week 1-3):  Phase 1 — 출처 추적, 해시 기반 캐시, 중복 집계
│                      └── v1.0.6 릴리즈
│   Week 1: 출처 추적 (Provenance) 구현
│   Week 2: 해시 기반 전역 캐시 개선 + 중복 집계
│   Week 3: 통합 테스트, UI 연동 (중복 통계 탭)
│
├── 3월 (Week 4-8):  Phase 2 — 구조화된 파싱, 블록 단위 중복, 배치 최적화
│                      └── v1.1.0-alpha
│   Week 4-5: StructuredBlockParser 구현
│   Week 6-7: 블록 단위 중복 판정 모드
│   Week 8: 배치 중단 최적화 + 통합 테스트
│
└── 4월~5월 (Week 9-16): Phase 3 — 이중 출력, 유연 중복, SQLite 마이그레이션
                           └── v1.1.0 릴리즈
    Week 9-10: DualOutputManager 구현
    Week 11-12: FlexibleDeduplicationStrategy 구현
    Week 13-14: CacheDatabase (SQLite) 구현
    Week 15-16: 성능 테스트, 대용량 데이터 검증, v1.1.0 릴리즈
```

---

## 6. 마일스톤 및 검증 기준

### Milestone 1: v1.0.6 (Phase 1 완료)
- [ ] 출처 추적 (Provenance) 구현
  - **검증**: `processed_state.json`에 `provenance` 필드 존재, 중복 라인의 발견 파일 목록 2개 이상 기록 확인
- [ ] 해시 기반 전역 캐시 개선
  - **검증**: `added_lines_cache`의 키가 SHA256 해시(64문자 hex)인지 확인, 메모리 사용량 30% 이상 감소 확인 (`psutil` 측정)
- [ ] 중복 집계 (`duplicate_stats`) 구현
  - **검증**: UI "중복 통계" 탭에 "TOP 10 중복 라인" 표시, `duplicate_count` 정확히 집계
- [ ] 기존 16개 테스트 + 신규 테스트 통과

### Milestone 2: v1.1.0-alpha (Phase 2 완료)
- [ ] StructuredBlockParser 구현
  - **검증**: EzQ 형식 백업 파일(`송신:`, `시간:`, `제목:`, `내용:`) 파싱 시 4개 필드 모두 추출 확인
- [ ] 블록 단위 중복 판정 모드
  - **검증**: 동일 내용이어도 시간이 다륾 다른 블록으로 처리 (기존 라인 단위와 결과 비교)
- [ ] 배치 중단 최적화
  - **검증**: 10개 연속 파일이 95% 이상 중복이면 감시 간격이 1초 → 5초로 증가 확인

### Milestone 3: v1.1.0 (Phase 3 완료)
- [ ] 이중 출력 (Dual Output)
  - **검증**: `output/raw/`와 `output/deduped/` 폴더에 각각 파일 생성, HTML 리포트 생성
- [ ] 유연 중복 판정 (Flexible Deduplication)
  - **검증**: "시간 제외 중복 판정" ON 시, 시간만 다른 동일 내용이 중복으로 처리되는지 확인
- [ ] SQLite 캐시 마이그레이션
  - **검증**: 100,000줄 캐시 로드 시 JSON 대비 50% 이상 빠른 로드 시간, 메모리 사용량 안정
- [ ] 기존 사용자 설정 호환성 (마이그레이션 테스트)

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 대응 전략 |
|---|---|---|
| **해시 충돌** (SHA256 이론상 가능) | 낮음 | SHA256 충돌 확률은 현실적으로 0에 가까움. 만약 우려된다면 `hash + line_preview` 이중 확인 |
| **SQLite 도입 시 기존 JSON 캐시 마이그레이션 실패** | 중간 | `load_line_cache()`에서 JSON → SQLite 자동 마이그레이션, 실패 시 백업 복원 |
| **블록 단위 중복 시 성능 저하** | 중간 | 블록 파싱은 선택적 모드(`content_parsing_mode`)로 제공, 기본은 라인 단위 유지 |
| **메모리 사용량 증가 (출처 추적)** | 낮음 | 출처는 `processed_state.json`에만 저장, 메모리에는 해시 세트만 유지. SQLite 마이그레이션 시 메모리 안정 |
| **기존 사용자 설정 호환성** | 중간 | `normalize_config_data`에 새 필드 추가, 기본값으로 하위 호환성 유지 |

---

## 8. 결론

현재 프로젝트는 **실시간 증분 처리**와 **파일 재생성 감지**라는 강력한 기반 위에, **라인 단위 중복 감지**를 구현했습니다. 이는 단순 텍스트 로그 수집에는 매우 효율적입니다.

EzQ 설계는 **의미 단위 중복 감지(블록 단위)**와 **출처 추적(Provenance)**, **메타데이터 활용**이라는 장점을 제공합니다. 이는 구조화된 데이터(메신저 백업, 폼 데이터 등) 처리에 적합합니다.

**혼합안의 핵심**은 다음과 같습니다:

1. **단기**: 현재 라인 단위 처리를 유지하면서, 해시 기반 캐시로 메모리 최적화하고 출처 추적으로 데이터 계보를 확보합니다.
2. **중기**: 사용자 선택적으로 "구조화된 파싱 모드"를 제공하여, EzQ와 같은 블록 단위 중복 감지를 지원합니다.
3. **장기**: SQLite 기반 영속성으로 대용량 데이터를 안정적으로 처리하고, 유연한 중복 판정 전략으로 다양한 업무 맥락을 수용합니다.

**즉각적인 사용자 가치**: Phase 1만 적용해도 "이 라인은 어떤 파일에서 발견됐는가?"라는 질문에 답할 수 있게 되고, 메모리 효율이 개선되어 더 많은 라인을 캐싱할 수 있게 됩니다.

> **다음 행동**: `feat/deduplication-improvements` 브랜치를 생성하여 Phase 1의 출처 추적(P1)부터 구현을 시작합니다.
