import hashlib
from typing import Dict, List, Optional
from src.auto_write_txt_to_docs.block_parser import StructuredBlock


class FlexibleDeduplicationStrategy:
    def __init__(self, ignore_fields: Optional[List[str]] = None):
        self.ignore_fields = set(ignore_fields or [])

    def compute_fingerprint(self, block: StructuredBlock, context: str = "") -> str:
        fields = dict(block.fields)
        for field in self.ignore_fields:
            fields.pop(field, None)
        
        values = [context] + [f"{k}={v}" for k, v in sorted(fields.items())]
        payload = "\n".join(values)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_new_blocks(self, blocks: List[StructuredBlock], cache: Dict[str, StructuredBlock], context: str = "") -> List[StructuredBlock]:
        new_blocks = []
        for block in blocks:
            fp = self.compute_fingerprint(block, context)
            if fp not in cache:
                new_blocks.append(block)
        return new_blocks

    def remember_blocks(self, blocks: List[StructuredBlock], cache: Dict[str, StructuredBlock], context: str = ""):
        for block in blocks:
            fp = self.compute_fingerprint(block, context)
            if fp in cache:
                cache.move_to_end(fp)
            else:
                cache[fp] = block


def get_flexible_strategy(config: Optional[Dict] = None) -> Optional[FlexibleDeduplicationStrategy]:
    if config is None:
        return None
    enabled = config.get("flexible_dedup", {}).get("enabled", False)
    if not enabled:
        return None
    ignore_fields = config.get("flexible_dedup", {}).get("ignore_fields", [])
    return FlexibleDeduplicationStrategy(ignore_fields)
