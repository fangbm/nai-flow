from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from .config import settings
from .schemas import ImageRequest, ScriptRequest, StoryPage


@lru_cache(maxsize=1)
def _nai5_storyboard_skill() -> str:
    skill_path = Path(__file__).with_name("nai5_storyboard_skill.md")
    try:
        return skill_path.read_text(encoding="utf-8")
    except OSError:
        return "Apply NovelAI V5 storyboard best practices: clear role attribution, one frozen moment per panel, and no appearance details."


def _authorization(token: str) -> str:
    return f"Bearer {token.removeprefix('Bearer ').strip()}"


def _chat_completions_url(endpoint: str) -> str:
    """Accept either an OpenAI-compatible base URL or its full chat endpoint."""
    endpoint = endpoint.rstrip("/")
    return endpoint if endpoint.endswith("/chat/completions") else f"{endpoint}/chat/completions"


async def generate_image(payload: ImageRequest) -> tuple[bytes, str]:
    if not settings.nai_token:
        raise HTTPException(status_code=409, detail="后端尚未配置 NovelAI Token")
    request_body = {
        "input": payload.input,
        "model": payload.model,
        "action": "generate",
        "parameters": payload.parameters,
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                settings.nai_endpoint,
                headers={"Authorization": _authorization(settings.nai_token), "Accept": "application/zip, image/png"},
                json=request_body,
            )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"NovelAI 网络请求失败：{error}") from error
    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="NovelAI Token 无效或已过期。请在连接设置中用新的 Persistent API Token（通常以 pst 开头）覆盖后保存。",
        )
    if response.status_code == 429:
        retry_after = response.headers.get("retry-after")
        wait_hint = f"请等待 {retry_after} 秒后再试。" if retry_after else "请稍候后再试，避免重复点击生成。"
        headers = {"Retry-After": retry_after} if retry_after else None
        detail = response.text[:12000].strip() or "上游未返回错误正文"
        raise HTTPException(status_code=429, detail=f"NovelAI 当前限流。{wait_hint}\n\n上游返回：{detail}", headers=headers)
    if response.is_error:
        detail = response.text[:12000].strip() or "上游未返回错误正文"
        raise HTTPException(status_code=response.status_code, detail=f"NovelAI {response.status_code}：{detail}")
    return response.content, response.headers.get("content-type", "application/zip")


async def resolve_characters(characters: str) -> list[dict]:
    if not (settings.llm_token and settings.llm_endpoint and settings.llm_model):
        raise HTTPException(status_code=409, detail="未配置剧本文本模型，无法识别角色英文名")
    system = (
        'You resolve character names for NovelAI V5 Character fields. Return JSON only: '
        '{"characters":[{"input":"original Chinese name","english_name":"English or romaji name",'
        '"series":"franchise title","nai_character":"English name (Franchise)",'
        '"confidence":"high|uncertain"}]}. '
        'For every supplied Chinese character, identify its official English/romaji name and franchise when known. '
        'Do not invent a franchise, translation, or tag. If uncertain, preserve the input in english_name, leave series empty, '
        'set nai_character to the input, and mark confidence uncertain. '
        'Do not include appearance, personality, actions, or prose.'
    )
    endpoint = _chat_completions_url(settings.llm_endpoint)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": _authorization(settings.llm_token)},
                json={"model": settings.llm_model, "messages":[{"role":"system", "content":system}, {"role":"user", "content":f"Resolve these character names: {characters}"}], "temperature":0, "response_format":{"type":"json_object"}},
            )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"角色名称识别网络请求失败：{error}") from error
    if response.is_error:
        detail = response.text[:12000].strip() or "上游未返回错误正文"
        raise HTTPException(status_code=response.status_code, detail=f"角色名称识别模型 {response.status_code}（{endpoint}）：{detail}")
    try:
        output = json.loads(response.json()["choices"][0]["message"]["content"])
        resolved = output["characters"]
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="角色名称识别模型没有返回有效 JSON") from error
    if not isinstance(resolved, list) or not resolved:
        raise HTTPException(status_code=502, detail="角色名称识别模型返回缺少 characters")
    normalized = []
    for item in resolved[:10]:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "input": str(item.get("input", "")).strip(),
            "english_name": str(item.get("english_name", "")).strip(),
            "series": str(item.get("series", "")).strip(),
            "nai_character": str(item.get("nai_character", "")).strip(),
            "confidence": "high" if item.get("confidence") == "high" else "uncertain",
        })
    if not normalized:
        raise HTTPException(status_code=502, detail="角色名称识别模型未返回可用角色")
    return normalized


async def generate_storyboard(payload: ScriptRequest) -> dict | None:
    if not (settings.llm_token and settings.llm_endpoint and settings.llm_model):
        return None
    system = (
        'You are a manga storyboard editor. Return JSON only: '
        '{"pages":[{"title":"Chinese title","beat":"Chinese page beat",'
        '"continuity":"Chinese visual carry-over note","panels":["English NovelAI V5 visual prompt", ...]}]}. '
        'Build continuous story pages. Each panel must be a concise visual direction. '
        'Use Character 1, Character 2, and so on in every panel. These indexes match the separate NovelAI Character fields. '
        'Never use a supplied role name in any panel. '
        'Character appearance is controlled separately by NovelAI Character fields: never describe hair, eyes, '
        'face, body, clothing, accessories, colors, or physical appearance. '
        'Each panel is exactly one frozen moment, never a sequence, montage, transition, or "then cut to". '
        'State which Character N performs each action and who receives it; for shared objects, state whose hand holds it. '
        'Use concise English visual prompts containing pose tags, one camera tag, setting, lighting, and named-role relationships. '
        'Avoid dialogue text. '
        'For each page, add a short Chinese continuity note naming the prop, direction, lighting, or reaction that carries into the next page. '
        'Exact requested page and panel count.\n\n'
        'The following is a mandatory local NAI V5 storyboarding skill. Follow it over generic writing habits:\n'
        f'{_nai5_storyboard_skill()}'
    )
    prompt = (
        f"Synopsis: {payload.synopsis}\n"
        f"Role names (identity only; do not repeat their appearance):\n{payload.characters}\n"
        f"Visual anchor (fixed style, era, location, and lighting rules): {payload.visual_anchor or 'No extra anchor'}\n"
        f"Continuity anchor (must recur across pages): {payload.continuity_anchor or 'Use a visible prop, direction, lighting, or reaction'}\n"
        f"Page layout: {payload.layout or 'Use the requested panel count with clear position anchors'}\n"
        f"Pages: {payload.pages}\nPanels per page: {payload.panels}"
    )
    endpoint = _chat_completions_url(settings.llm_endpoint)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": _authorization(settings.llm_token)},
                json={"model": settings.llm_model, "messages":[{"role":"system", "content":system}, {"role":"user", "content":prompt}], "temperature":0.8, "response_format":{"type":"json_object"}},
            )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"剧本文本模型网络请求失败：{error}") from error
    if response.is_error:
        detail = response.text[:12000].strip() or "上游未返回错误正文"
        raise HTTPException(status_code=response.status_code, detail=f"剧本文本模型 {response.status_code}（{endpoint}）：{detail}")
    content = ""
    try:
        content = response.json()["choices"][0]["message"]["content"]
        output = json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raw = content if isinstance(content, str) and content else response.text
        raise HTTPException(status_code=502, detail=f"剧本文本模型没有返回有效的 JSON 分镜。原始返回：{raw[:12000]}") from error
    raw_pages = output.get("pages")
    if not isinstance(raw_pages, list):
        raise HTTPException(status_code=502, detail=f"剧本文本模型返回缺少 pages。原始返回：{content[:12000]}")
    if len(raw_pages) != payload.pages:
        raise HTTPException(
            status_code=502,
            detail=f"剧本文本模型返回了 {len(raw_pages)} 页，但请求的是 {payload.pages} 页。请重新生成。原始返回：{content[:12000]}",
        )
    pages = []
    for index, raw_page in enumerate(raw_pages, start=1):
        try:
            page = StoryPage.model_validate(raw_page)
        except ValidationError as error:
            raise HTTPException(
                status_code=502,
                detail=f"剧本文本模型返回的第 {index} 页格式无效：{error.errors(include_url=False)}。原始返回：{content[:12000]}",
            ) from error
        if len(page.panels) != payload.panels:
            raise HTTPException(
                status_code=502,
                detail=f"剧本文本模型第 {index} 页返回了 {len(page.panels)} 格，但请求的是 {payload.panels} 格。请重新生成。原始返回：{content[:12000]}",
            )
        pages.append({"title": page.title, "beat": page.beat, "continuity": page.continuity, "panels": page.panels})
    return {"pages": pages}
