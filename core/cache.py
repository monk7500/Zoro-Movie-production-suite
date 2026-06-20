import hashlib, json, os, tempfile, shutil
from pathlib import Path
from typing import Dict, Optional

class ContentCache:
    def __init__(self, cache_root: Path):
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def run_key(self, agent_name: str, model_version: str, input_slices: Dict) -> str:
        hasher = hashlib.sha256()
        hasher.update(agent_name.encode())
        hasher.update(model_version.encode())
        for name in sorted(input_slices.keys()):
            hasher.update(name.encode())
            hasher.update(json.dumps(input_slices[name], sort_keys=True).encode())
        return hasher.hexdigest()

    def get(self, agent_name: str, run_key: str) -> Optional[dict]:
        meta_path = self.cache_root / agent_name / run_key / "metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                return json.load(f)
        return None

    def put(self, agent_name: str, run_key: str, metadata: dict, output_files: Dict[str, bytes]):
        out_dir = self.cache_root / agent_name / run_key
        out_dir.mkdir(parents=True, exist_ok=True)
        for fname, data in output_files.items():
            out_path = out_dir / fname
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
        with open(out_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

    def _has_disk_space(self, path: Path, required_bytes: int) -> bool:
        try:
            usage = shutil.disk_usage(path)
            return usage.free > required_bytes + 100*1024*1024
        except:
            return True
