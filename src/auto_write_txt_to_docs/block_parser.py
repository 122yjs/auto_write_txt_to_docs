import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class StructuredBlock:
    fields: Dict[str, str] = field(default_factory=dict)
    raw_text: str = ""
    source_file: str = ""

    def get_fingerprint(self, context: str = "") -> str:
        if self.fields:
            values = [context] + [f"{k}={v}" for k, v in sorted(self.fields.items())]
        else:
            values = [context, self.raw_text]
        payload = "\n".join(values)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class StructuredBlockParser:
    def __init__(
        self,
        block_separator: str = "-------------------------------------------------------------------------------",
        field_patterns: Optional[Dict[str, str]] = None,
    ):
        self.block_separator = block_separator
        self.field_patterns = field_patterns or {}
        self.compiled_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.field_patterns.items()
        }

    def parse(self, content: str, source_file: str = "") -> List[StructuredBlock]:
        if not content or not content.strip():
            return []

        raw_blocks = content.split(self.block_separator)
        blocks = []
        for raw_block in raw_blocks:
            stripped = raw_block.strip()
            if not stripped:
                continue

            fields = self._extract_fields(stripped)
            blocks.append(StructuredBlock(
                fields=fields,
                raw_text=self._build_display_text(stripped, fields),
                source_file=source_file,
            ))
        return blocks

    def _build_display_text(self, block_text: str, fields: Dict[str, str]) -> str:
        lines = [line.strip() for line in block_text.splitlines() if line.strip()]
        if not lines:
            return ""

        lines = self._remove_embedded_reply_original(lines)
        title_value = fields.get("title") or self._extract_label_value(lines, "제목")
        body_value = fields.get("body") or self._extract_label_value(lines, "내용")
        if title_value and body_value and title_value.strip() == body_value.strip():
            title_index = self._find_label_line_index(lines, "제목")
            if title_index is not None:
                lines.pop(title_index)

        return "\n".join(lines)

    def _remove_embedded_reply_original(self, lines: List[str]) -> List[str]:
        marker_index = self._find_reply_original_marker_index(lines)
        if marker_index is not None:
            return lines[:marker_index]

        ezq_original = self._find_ezq_reply_original(lines)
        if ezq_original is not None:
            original_index, reply_context_line = ezq_original
            return self._insert_reply_context_line(lines[:original_index], reply_context_line)

        embedded_index = self._find_embedded_message_header_index(lines)
        if embedded_index is not None:
            return lines[:embedded_index]

        return lines

    def _find_reply_original_marker_index(self, lines: List[str]) -> Optional[int]:
        marker_pattern = re.compile(
            r"(원문|이전\s*메시지|이전\s*쪽지|전달된\s*메시지|original\s+message|forwarded\s+message)",
            re.IGNORECASE,
        )
        for index, line in enumerate(lines):
            if marker_pattern.search(line):
                return index
        return None

    def _find_ezq_reply_original(self, lines: List[str]) -> Optional[Tuple[int, str]]:
        first_body_index = self._find_label_line_index(lines, "내용")
        if first_body_index is None:
            return None

        for index in range(first_body_index + 1, len(lines)):
            if self._is_dash_separator_line(lines[index]):
                header_lines = lines[index + 1:index + 5]
                if self._has_ezq_reply_header(header_lines):
                    return index, self._build_reply_context_line(header_lines)
                continue

            header_lines = lines[index:index + 5]
            if self._is_ezq_reply_sender_line(lines[index]) and self._has_ezq_reply_header(header_lines):
                return index, self._build_reply_context_line(header_lines)

        return None

    def _insert_reply_context_line(self, current_lines: List[str], reply_context_line: str) -> List[str]:
        if not reply_context_line:
            return current_lines

        insert_index = self._find_label_line_index(current_lines, "내용")
        if insert_index is None:
            return current_lines + [reply_context_line]

        return current_lines[:insert_index] + [reply_context_line] + current_lines[insert_index:]

    def _has_ezq_reply_header(self, candidate_lines: List[str]) -> bool:
        normalized_labels = {
            self._normalize_label_name(self._get_label_name(line))
            for line in candidate_lines
        }
        return "발신자" in normalized_labels and "날짜" in normalized_labels

    def _is_ezq_reply_sender_line(self, line: str) -> bool:
        return self._normalize_label_name(self._get_label_name(line)) == "발신자"

    def _is_dash_separator_line(self, line: str) -> bool:
        return bool(re.fullmatch(r"\s*-{5,}\s*", line))

    def _normalize_label_name(self, label: str) -> str:
        return re.sub(r"\s+", "", label or "")

    def _build_reply_context_line(self, header_lines: List[str]) -> str:
        sender = self._clean_reply_sender(self._extract_normalized_label_value(header_lines, "발신자"))
        date_text = self._format_reply_date(self._extract_normalized_label_value(header_lines, "날짜"))

        if sender and date_text:
            return f"답장: {sender}님의 {date_text} 메시지에 대한 답장"
        if sender:
            return f"답장: {sender}님의 메시지에 대한 답장"
        if date_text:
            return f"답장: {date_text} 메시지에 대한 답장"
        return "답장: 이전 메시지에 대한 답장"

    def _extract_normalized_label_value(self, lines: List[str], normalized_label: str) -> str:
        for line in lines:
            if self._normalize_label_name(self._get_label_name(line)) != normalized_label:
                continue
            match = re.match(r"^\s*[^:：]{1,20}\s*[:：]\s*(.*)$", line)
            if match:
                return match.group(1).strip()
        return ""

    def _clean_reply_sender(self, sender_text: str) -> str:
        return re.sub(r"\[.*$", "", sender_text or "").strip()

    def _format_reply_date(self, date_text: str) -> str:
        match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", date_text or "")
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return (date_text or "").strip()

    def _find_embedded_message_header_index(self, lines: List[str]) -> Optional[int]:
        first_sender_index = self._find_label_line_index(lines, "송신")
        first_body_index = self._find_label_line_index(lines, "내용")
        if first_sender_index is None or first_body_index is None:
            return None

        for index in range(first_body_index + 1, len(lines) - 1):
            if not self._is_label_line(lines[index], "송신"):
                continue
            next_labels = {
                self._get_label_name(line)
                for line in lines[index + 1:index + 4]
            }
            if "시간" in next_labels or "내용" in next_labels:
                return index
        return None

    def _extract_label_value(self, lines: List[str], label: str) -> str:
        label_pattern = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.*)$")
        for line in lines:
            match = label_pattern.match(line)
            if match:
                return match.group(1).strip()
        return ""

    def _find_label_line_index(self, lines: List[str], label: str) -> Optional[int]:
        label_pattern = re.compile(rf"^\s*{re.escape(label)}\s*:")
        for index, line in enumerate(lines):
            if label_pattern.match(line):
                return index
        return None

    def _is_label_line(self, line: str, label: str) -> bool:
        return self._get_label_name(line) == label

    def _get_label_name(self, line: str) -> str:
        match = re.match(r"^\s*([^:：]{1,20})\s*[:：]", line)
        return match.group(1).strip() if match else ""

    def _extract_fields(self, block_text: str) -> Dict[str, str]:
        fields = {}
        lines = block_text.splitlines()
        for line in lines:
            for name, pattern in self.compiled_patterns.items():
                match = pattern.match(line)
                if match:
                    fields[name] = match.group(1).strip()
                    break
        return fields

    def get_required_fields(self) -> List[str]:
        return list(self.field_patterns.keys())

    def validate_block(self, block: StructuredBlock) -> Tuple[bool, Optional[str]]:
        required = self.get_required_fields()
        missing = [f for f in required if f not in block.fields or not block.fields[f]]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        return True, None
