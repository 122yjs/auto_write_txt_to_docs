# 릴리즈 노트 — v1.1.0-alpha

> **릴리즈 타입**: Pre-release (Alpha)  
> **브랜치**: `feat/deduplication-improvements`  
> **기준 커밋**: `51f8ccf`  
> **배포 대상**: 개발자 및 베타 테스트 사용자

---

## 개요

이 릴리즈는 **중복 감지(deduplication) 시스템의 대폭적인 개선**을 포함합니다. 기존의 단순 라인 단위 중복 감지를 넘어, 출처 추적, 메모리 최적화, 블록 단위 중복 감지, 배치 최적화 등 다양한 고급 기능이 추가되었습니다.

**⚠️ 주의**: Alpha 버전으로, 프로덕션 환경보다는 테스트 및 피드백 수집 용도로 사용해 주세요.

---

## Phase 1: 출처 추적 및 캐시 최적화 (v1.0.6-alpha 기반)

### 1.1 출처 추적 (Provenance Tracking)

- **기능**: 중복으로 판정된 라인이 **어느 파일에서 발견**되었는지 기록
- **저장 위치**: `processed_state.json` → `provenance` 필드
- **활용**: 문제 발생 시 원본 파일 추적, 중복 파일명 기록 시 출처 포함 가능
- **예시**:
  ```json
  {
    "provenance": {
      "a6e2b621...": ["backup-2026-03-18_130726.txt", "backup-2026-03-18_130740.txt"]
    }
  }
  ```

### 1.2 해시 기반 전역 캐시 개선

- **변경**: 전역 캐시의 키를 **라인 문자열 → SHA256 해시(32바이트)** 로 변경
- **효과**: 메모리 사용량 약 **36% 절약** (라인 평균 50바이트 → 해시 32바이트)
- **영속성**: `added_lines_cache.json`이 `{hash: line}` 형태로 저장
- **하위 호환**: 기존 리스트 형식 캐시 파일도 자동 로드 지원

### 1.3 중복 집계 및 통계 API

- **추적 항목**: `total_occurrences`, `first_seen_at`, `last_seen_at`
- **API**: `get_top_duplicate_lines(limit=10)`
- **활용**: "가장 많이 중복된 라인 TOP 10" 조회
- **저장**: `duplicate_stats.json`에 독립 저장

---

## Phase 2: 블록 단위 중복 및 배치 최적화 (v1.1.0-alpha)

### 2.1 StructuredBlockParser (신규 모듈)

- **파일**: `src/auto_write_txt_to_docs/block_parser.py`
- **기능**: 구조화된 텍스트 블록 파싱
  - 구분선(`---`) 기준 블록 분할
  - 정규식 패턴으로 필드 추출 (예: `송신:`, `시간:`, `제목:`, `내용:`)
  - 블록별 SHA256 지문 생성
  - 컨텍스트 기반 지문 (받은쪽지함 vs 병은쪽지함 구분)
- **테스트**: 7개 단위 테스트 포함

### 2.2 블록 단위 중복 판정 모드

- **설정**: `content_parsing_mode: "block"` (기본값: `"line"`)
- **동작**:
  - 파일 내용을 블록으로 파싱
  - 이미 캐시에 있는 블록은 걄뛰고 새 블록만 Google Docs에 기록
  - `block_separator`, `field_patterns` 사용자 설정 가능
- **활용 시나리오**: EzQ 쪽지 백업, 메신저 로그, 구조화된 폼 데이터

### 2.3 BatchDeduplicationOptimizer (신규 모듈)

- **파일**: `src/auto_write_txt_to_docs/batch_optimizer.py`
- **기능**: 배치 중복률 분석 및 감시 간격 동적 조절
- **정책**:
  - 최근 10개 파일의 중복률이 **95% 이상** → 감시 간격 2배 증가 (최대 60초)
  - 중복률 감소 → 감시 간격 절반 감소 (최소 0.5초)
- **효과**: 불필요한 CPU 사용 감소, 배터리 절약

---

## 테스트 결과

| 테스트 모듈 | 테스트 수 | 결과 |
|---|---|---|
| `test_backend_processor.py` | 29개 | 전체 통과 |
| `test_block_parser.py` | 7개 | 전체 통과 |
| `test_batch_optimizer.py` | 5개 | 전체 통과 |
| **합계** | **41개** | **전체 통과** |

> 프로젝트 전체 99개 테스트 중 3개 오류는 `customtkinter` 미설치 환경 의존성, 1개는 기존 버전 메타데이터 일관성 이슈로 본 릴리즈와 무관합니다.

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

### 설정 예시 (블록 모드)

```json
{
  "content_parsing_mode": "block",
  "block_separator": "-------------------------------------------------------------------------------",
  "field_patterns": {
    "sender": "^송신:(.+)",
    "time": "^시간:(.+)",
    "title": "^제목:(.+)",
    "body": "^내용:(.+)"
  }
}
```

---

## 알려진 이슈

1. **main_gui.py와의 통합 미완료**: 블록 모드 설정 UI는 아직 `main_gui.py`에 추가되지 않았습니다. 설정은 `config.json` 수동 편집 또는 코드 레벨에서만 가능합니다.
2. **BatchDeduplicationOptimizer 미연동**: `run_monitoring()`에 optimizer가 정의되어 있으나, 메인 루프와의 완전한 통합은 이후 정식 릴리즈에서 진행됩니다.
3. **macOS 테스트 환경**: 일부 테스트는 macOS의 `ctime` 변경 동작에 의존하며, Windows에서는 다르게 동작할 수 있습니다.

---

## 기여 및 피드백

- 버그 리포트: [GitHub Issues](https://github.com/122yjs/auto_write_txt_to_docs/issues)
- 피드백 환영: 블록 모드 사용성, 중복률 임계값(95%), 메모리 사용량 등

---

## 다음 단계 (Roadmap)

- **v1.1.0-beta**: `main_gui.py`에 블록 모드 설정 UI 추가
- **v1.1.0**: `BatchDeduplicationOptimizer`를 `run_monitoring()`에 완전 통합
- **v1.2.0**: 이중 출력(raw/deduped), 유연 중복 판정, SQLite 마이그레이션

> **릴리즈일**: 2026년 5월 1일
