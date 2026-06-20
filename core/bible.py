import json, os, tempfile, re
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, List

class FilmBible:
    def __init__(self, bible_dir: Path):
        self.bible_dir = Path(bible_dir)
        self.bible_dir.mkdir(parents=True, exist_ok=True)
        self.versions_file = self.bible_dir / "current_version.txt"

    @property
    def current_version(self) -> str:
        if self.versions_file.exists():
            return self.versions_file.read_text().strip()
        return "v0001"

    @current_version.setter
    def current_version(self, version: str):
        self.versions_file.write_text(version)

    def list_versions(self) -> List[str]:
        return sorted([f.stem for f in self.bible_dir.glob("v*.json")])

    def read(self, version: Optional[str] = None) -> dict:
        v = version or self.current_version
        path = self.bible_dir / f"{v}.json"
        if not path.exists():
            return self._empty_template()
        with open(path) as f:
            return json.load(f)

    def _empty_template(self) -> dict:
        return {
            "meta": {"script_raw": "", "mode": "cinematic", "fix_versions": {}},
            "parsed_script": {"scenes": [], "characters": [], "entities": [], "props": []},
        }

    def write(self, data: dict) -> str:
        versions = self.list_versions()
        next_num = 1 if not versions else int(versions[-1][1:]) + 1
        new_version = f"v{next_num:04d}"
        new_path = self.bible_dir / f"{new_version}.json"
        tmp_fd, tmp_name = tempfile.mkstemp(dir=self.bible_dir, suffix=".json")
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_name, new_path)
        except:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise
        self.current_version = new_version
        return new_version

    def extract_slice(self, json_path_expr: str, version: Optional[str] = None) -> Any:
        data = self.read(version)
        parts = json_path_expr.split(".")
        for part in parts:
            match = re.match(r"(\w+)\[(\d+)\]", part)
            if match:
                name, index = match.groups()
                try:
                    data = data[name][int(index)]
                except:
                    return None
            else:
                if isinstance(data, dict):
                    if part not in data:
                        return None
                    data = data[part]
                elif isinstance(data, list):
                    try:
                        data = data[int(part)]
                    except:
                        return None
                else:
                    return None
        return data
