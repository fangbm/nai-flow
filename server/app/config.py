from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


SERVER_DIR = Path(__file__).resolve().parent.parent


@dataclass
class ProviderSettings:
    nai_token: str = ""
    nai_endpoint: str = "https://image.novelai.net/ai/generate-image"
    llm_token: str = ""
    llm_endpoint: str = ""
    llm_model: str = ""

    @property
    def store_dir(self) -> Path:
        return SERVER_DIR / "store"

    @property
    def settings_file(self) -> Path:
        return self.store_dir / "settings.json"

    @property
    def project_file(self) -> Path:
        return self.store_dir / "project.json"

    @property
    def assets_dir(self) -> Path:
        return self.store_dir / "assets"

    def load(self) -> None:
        self.nai_token = os.getenv("NAI_TOKEN", self.nai_token)
        self.nai_endpoint = os.getenv("NAI_ENDPOINT", self.nai_endpoint)
        self.llm_token = os.getenv("LLM_API_KEY", self.llm_token)
        self.llm_endpoint = os.getenv("LLM_ENDPOINT", self.llm_endpoint)
        self.llm_model = os.getenv("LLM_MODEL", self.llm_model)
        if not self.settings_file.exists():
            return
        try:
            payload = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for key, value in payload.items():
            if key in asdict(self) and isinstance(value, str):
                setattr(self, key, value)

    def save(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.settings_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.settings_file)

    def load_project(self) -> dict | None:
        if not self.project_file.exists():
            return None
        try:
            payload = json.loads(self.project_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def save_project(self, project: dict) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.project_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.project_file)

    @staticmethod
    def validate_endpoint(value: str, label: str, *, optional: bool = False) -> str:
        value = value.strip()
        if optional and not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{label}必须是完整的 http(s) URL")
        return value

    @staticmethod
    def mask(value: str) -> str:
        if not value:
            return ""
        return "****" if len(value) <= 8 else f"{value[:4]}****{value[-4:]}"

    def view(self) -> dict:
        return {
            "nai": {
                "endpoint": self.nai_endpoint,
                "configured": bool(self.nai_token),
                "token_masked": self.mask(self.nai_token),
            },
            "llm": {
                "endpoint": self.llm_endpoint,
                "model": self.llm_model,
                "configured": bool(self.llm_token and self.llm_endpoint and self.llm_model),
                "token_masked": self.mask(self.llm_token),
            },
        }


settings = ProviderSettings()
