import os
import json
from datetime import datetime
from typing import List, Optional


class DualOutputManager:
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            base_dir = os.path.expanduser("~")
            output_dir = os.path.join(base_dir, "AppData", "Roaming", "MessengerDocsAutoWriter", "output")
            if not os.path.exists(os.path.dirname(output_dir)):
                output_dir = os.path.join(base_dir, ".messenger_docs_output")
        self.output_dir = output_dir
        self.raw_dir = os.path.join(output_dir, "raw")
        self.deduped_dir = os.path.join(output_dir, "deduped")
        self.html_dir = os.path.join(output_dir, "html")
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.deduped_dir, exist_ok=True)
        os.makedirs(self.html_dir, exist_ok=True)

    def _get_filename(self, prefix: str, ext: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{date_str}_{prefix}.{ext}"

    def write_raw(self, filepath: str, lines: List[str], timestamp: Optional[datetime] = None):
        if not lines:
            return
        filename = self._get_filename("raw", "txt")
        full_path = os.path.join(self.raw_dir, filename)
        t = timestamp or datetime.now()
        header = f"# 파일: {os.path.basename(filepath)} | 시간: {t.strftime('%Y-%m-%d %H:%M:%S')}\n"
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(lines) + "\n\n")

    def write_deduped(self, filepath: str, lines: List[str], duplicate_count: int = 0, timestamp: Optional[datetime] = None):
        if not lines:
            return
        filename = self._get_filename("deduped", "txt")
        full_path = os.path.join(self.deduped_dir, filename)
        t = timestamp or datetime.now()
        header = f"# 파일: {os.path.basename(filepath)} | 중복 제거: {duplicate_count}줄 | 시간: {t.strftime('%Y-%m-%d %H:%M:%S')}\n"
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(lines) + "\n\n")

    def generate_html(self, date_str: Optional[str] = None, log_func=None) -> str:
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        deduped_file = os.path.join(self.deduped_dir, f"{date_str}_deduped.txt")
        raw_file = os.path.join(self.raw_dir, f"{date_str}_raw.txt")
        
        deduped_content = ""
        if os.path.exists(deduped_file):
            with open(deduped_file, "r", encoding="utf-8") as f:
                deduped_content = f.read()
        
        raw_content = ""
        if os.path.exists(raw_file):
            with open(raw_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
        
        html_path = os.path.join(self.html_dir, f"{date_str}_report.html")
        html = self._build_html(date_str, deduped_content, raw_content)
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        if log_func:
            log_func(f"HTML 리포트 생성 완료: {html_path}")
        
        return html_path

    def _build_html(self, date_str: str, deduped_content: str, raw_content: str) -> str:
        deduped_lines = deduped_content.strip().split("\n") if deduped_content.strip() else []
        raw_lines = raw_content.strip().split("\n") if raw_content.strip() else []
        
        deduped_count = len([l for l in deduped_lines if l.strip() and not l.startswith("#")])
        raw_count = len([l for l in raw_lines if l.strip() and not l.startswith("#")])
        
        html_lines = [
            "<!DOCTYPE html>",
            "<html lang=\"ko\">",
            "<head>",
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f"    <title>메신저 문서 리포트 - {date_str}</title>",
            "    <style>",
            "        body { font-family: 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }",
            "        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
            "        h1 { color: #2563eb; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }",
            "        .stats { display: flex; gap: 20px; margin: 20px 0; }",
            "        .stat-card { flex: 1; background: #f8fafc; padding: 20px; border-radius: 8px; text-align: center; }",
            "        .stat-number { font-size: 32px; font-weight: bold; color: #2563eb; }",
            "        .stat-label { color: #64748b; margin-top: 5px; }",
            "        .section { margin-top: 30px; }",
            "        .section h2 { color: #1e293b; border-left: 4px solid #2563eb; padding-left: 12px; }",
            "        pre { background: #f1f5f9; padding: 20px; border-radius: 8px; overflow-x: auto; line-height: 1.6; }",
            "        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }",
            "        .badge-success { background: #dcfce7; color: #166534; }",
            "        .badge-info { background: #dbeafe; color: #1e40af; }",
            "    </style>",
            "</head>",
            "<body>",
            '    <div class="container">',
            f"        <h1>📄 메신저 문서 리포트 <span class=\"badge badge-info\">{date_str}</span></h1>",
            '        <div class="stats">',
            '            <div class="stat-card">',
            f"                <div class=\"stat-number\">{raw_count}</div>",
            '                <div class="stat-label">원본 라인 수</div>',
            "            </div>",
            '            <div class="stat-card">',
            f"                <div class=\"stat-number\">{deduped_count}</div>",
            '                <div class="stat-label">중복 제거 후</div>',
            "            </div>",
            '            <div class="stat-card">',
            f"                <div class=\"stat-number\">{raw_count - deduped_count}</div>",
            '                <div class="stat-label">제거된 중복</div>',
            "            </div>",
            "        </div>",
            '        <div class="section">',
            '            <h2>✅ 중복 제거된 내용</h2>',
            f"            <pre>{self._escape_html(deduped_content) if deduped_content else '(내용 없음)'}</pre>",
            "        </div>",
            '        <div class="section">',
            '            <h2>📋 원본 내용 (중복 포함)</h2>',
            f"            <pre>{self._escape_html(raw_content) if raw_content else '(내용 없음)'}</pre>",
            "        </div>",
            "    </div>",
            "</body>",
            "</html>",
        ]
        return "\n".join(html_lines)

    def _escape_html(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_dual_output_manager(config: Optional[dict] = None) -> Optional[DualOutputManager]:
    if config is None:
        return None
    enabled = config.get("dual_output_enabled", False)
    if not enabled:
        return None
    output_dir = config.get("dual_output_dir")
    return DualOutputManager(output_dir)
