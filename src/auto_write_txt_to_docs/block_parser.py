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
        values = [context] + [f"{k}={v}" for k, v in sorted(self.fields.items())]
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
                raw_text=stripped,
                source_file=source_file,
            ))
        return blocks

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
