from typing import Any, Literal

from pydantic import BaseModel, Field


class ProviderUpdate(BaseModel):
    token: str | None = Field(default=None, max_length=10000)
    endpoint: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, max_length=256)


class SettingsUpdate(BaseModel):
    nai: ProviderUpdate = Field(default_factory=ProviderUpdate)
    llm: ProviderUpdate = Field(default_factory=ProviderUpdate)


class ImageRequest(BaseModel):
    input: str = Field(min_length=1, max_length=20000)
    model: str = Field(min_length=1, max_length=256)
    parameters: dict[str, Any]


class ScriptRequest(BaseModel):
    synopsis: str = Field(min_length=1, max_length=10000)
    characters: str = Field(default="", max_length=4000)
    pages: int = Field(default=4, ge=1, le=20)
    panels: int = Field(default=4, ge=1, le=9)


class CharacterResolveRequest(BaseModel):
    characters: str = Field(min_length=1, max_length=4000)


class StoryPage(BaseModel):
    title: str = Field(default="新页面", max_length=300)
    beat: str = Field(default="", max_length=4000)
    panels: list[str] = Field(default_factory=list, max_length=9)
    pagePrompt: str = Field(default="", max_length=10000)
    image: str = Field(default="", max_length=2000)


class ProjectAsset(BaseModel):
    src: str = Field(min_length=1, max_length=2000)
    title: str = Field(default="素材", max_length=300)


class ProjectState(BaseModel):
    projectName: str = Field(default="未命名项目", max_length=300)
    view: Literal["studio", "comic", "assets"] = "studio"
    prompt: str = Field(default="", max_length=20000)
    negative: str = Field(default="", max_length=20000)
    characters: list[str] = Field(default_factory=list, max_length=10)
    model: str = Field(default="nai-diffusion-5-full", max_length=256)
    aspect: Literal["portrait", "square", "landscape", "wide"] = "portrait"
    samples: str = Field(default="1", max_length=3)
    steps: int = Field(default=28, ge=1, le=50)
    guidance: float = Field(default=5, ge=0, le=20)
    sampler: str = Field(default="k_euler_ancestral", max_length=100)
    seed: str = Field(default="", max_length=32)
    variety: bool = False
    synopsis: str = Field(default="", max_length=10000)
    comicCharacters: str = Field(default="", max_length=4000)
    pageCount: int = Field(default=4, ge=1, le=20)
    panelCount: int = Field(default=4, ge=1, le=9)
    pages: list[StoryPage] = Field(default_factory=list, max_length=20)
    assets: list[ProjectAsset] = Field(default_factory=list, max_length=200)


class ProjectUpdate(BaseModel):
    state: ProjectState
