from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


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
    def workspace_file(self) -> Path:
        return self.store_dir / "projects.json"

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
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _project_summary(project: dict) -> dict:
        state = project.get("state", {})
        return {
            "id": project["id"],
            "name": project["name"],
            "createdAt": project["createdAt"],
            "updatedAt": project["updatedAt"],
            "pageCount": len(state.get("pages", [])),
            "assetCount": len(state.get("assets", [])),
            "hasSynopsis": bool(str(state.get("synopsis", "")).strip()),
        }

    def _write_workspace(self, workspace: dict) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.workspace_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(workspace, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.workspace_file)

    def load_workspace(self) -> dict:
        """Load the multi-project workspace and migrate the old single project once."""
        if self.workspace_file.exists():
            try:
                payload = json.loads(self.workspace_file.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and isinstance(payload.get("projects"), list):
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        legacy = self.load_project()
        now = self._timestamp()
        project_id = uuid4().hex
        state = legacy or {"projectName": "未命名项目"}
        name = str(state.get("projectName") or "未命名项目").strip()[:300] or "未命名项目"
        workspace = {
            "activeProjectId": project_id,
            "projects": [{"id": project_id, "name": name, "createdAt": now, "updatedAt": now, "state": state}],
        }
        self._write_workspace(workspace)
        return workspace

    def workspace_summary(self) -> dict:
        workspace = self.load_workspace()
        return {
            "activeProjectId": workspace.get("activeProjectId"),
            "projects": [self._project_summary(project) for project in workspace["projects"]],
        }

    def get_workspace_project(self, project_id: str) -> dict | None:
        workspace = self.load_workspace()
        return next((project for project in workspace["projects"] if project["id"] == project_id), None)

    def create_workspace_project(self, name: str, state: dict) -> dict:
        workspace = self.load_workspace()
        now = self._timestamp()
        project = {"id": uuid4().hex, "name": name, "createdAt": now, "updatedAt": now, "state": state}
        workspace["projects"].insert(0, project)
        workspace["activeProjectId"] = project["id"]
        self._write_workspace(workspace)
        return project

    def save_workspace_project(self, project_id: str, state: dict) -> dict | None:
        workspace = self.load_workspace()
        project = next((item for item in workspace["projects"] if item["id"] == project_id), None)
        if project is None:
            return None
        project["state"] = state
        project["name"] = str(state.get("projectName") or project["name"]).strip()[:300] or project["name"]
        project["updatedAt"] = self._timestamp()
        workspace["activeProjectId"] = project_id
        self._write_workspace(workspace)
        return project

    def rename_workspace_project(self, project_id: str, name: str) -> dict | None:
        workspace = self.load_workspace()
        project = next((item for item in workspace["projects"] if item["id"] == project_id), None)
        if project is None:
            return None
        project["name"] = name
        project.setdefault("state", {})["projectName"] = name
        project["updatedAt"] = self._timestamp()
        self._write_workspace(workspace)
        return project

    def duplicate_workspace_project(self, project_id: str, name: str) -> dict | None:
        source = self.get_workspace_project(project_id)
        if source is None:
            return None
        state = dict(source.get("state", {}))
        state["projectName"] = name
        return self.create_workspace_project(name, state)

    def delete_workspace_project(self, project_id: str) -> bool:
        workspace = self.load_workspace()
        projects = workspace["projects"]
        if len(projects) <= 1:
            return False
        next_projects = [project for project in projects if project["id"] != project_id]
        if len(next_projects) == len(projects):
            return False
        workspace["projects"] = next_projects
        if workspace.get("activeProjectId") == project_id:
            workspace["activeProjectId"] = next_projects[0]["id"]
        self._write_workspace(workspace)
        return True

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
