from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from .config import settings
from .schemas import CharacterResolveRequest, ImageRequest, ProjectUpdate, ScriptRequest, SettingsUpdate
from .services import generate_image, generate_storyboard, resolve_characters

router = APIRouter()


def _openai_models_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/chat/completions"):
        return f"{endpoint.removesuffix('/chat/completions')}/models"
    return f"{endpoint}/models"


def _openai_chat_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    return endpoint if endpoint.endswith("/chat/completions") else f"{endpoint}/chat/completions"


def _is_html_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    prefix = response.content.lstrip()[:32].lower()
    return "text/html" in content_type or prefix.startswith((b"<!doctype html", b"<html"))


@router.get("/api/health")
async def health():
    return {"ok": True, **settings.view()}


@router.get("/api/settings")
async def read_settings():
    return settings.view()


@router.get("/api/project")
async def read_project():
    project = settings.load_project()
    if project is None:
        raise HTTPException(status_code=404, detail="尚未保存项目")
    return {"state": project}


@router.put("/api/project")
async def write_project(payload: ProjectUpdate):
    settings.save_project(payload.state.model_dump())
    return {"ok": True}


@router.post("/api/settings")
async def write_settings(payload: SettingsUpdate):
    try:
        if payload.nai.endpoint is not None:
            settings.nai_endpoint = settings.validate_endpoint(payload.nai.endpoint, "NovelAI 图片接口")
        if payload.nai.token:
            settings.nai_token = payload.nai.token.strip()
        if payload.llm.endpoint is not None:
            settings.llm_endpoint = settings.validate_endpoint(payload.llm.endpoint, "剧本文本接口", optional=True)
        if payload.llm.model is not None:
            settings.llm_model = payload.llm.model.strip()
        if payload.llm.token:
            settings.llm_token = payload.llm.token.strip()
        settings.save()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return settings.view()


@router.post("/api/settings/test/{provider}")
async def test_settings(provider: str, payload: SettingsUpdate | None = None):
    if provider == "nai":
        token_value = payload.nai.token.strip() if payload and payload.nai.token else settings.nai_token
        endpoint_value = payload.nai.endpoint if payload and payload.nai.endpoint is not None else settings.nai_endpoint
        if not token_value:
            raise HTTPException(status_code=409, detail="未配置 NovelAI Token")
        try:
            endpoint_value = settings.validate_endpoint(endpoint_value, "NovelAI 图片接口")
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        parsed = urlsplit(endpoint_value)
        account_url = f"{parsed.scheme}://{parsed.netloc}/user/information"
        token = token_value.removeprefix("Bearer ").strip()
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    account_url,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=f"NovelAI 连接测试失败：{error}") from error
        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="NovelAI Token 无效或已过期。请从 NovelAI 账户创建/复制 Persistent API Token（通常以 pst 开头），不要填写账户密码。",
            )
        if response.is_error:
            detail = response.text[:300].strip() or "上游未返回错误正文"
            raise HTTPException(status_code=response.status_code, detail=f"NovelAI 连接测试失败：{detail}")
        return {"ok": True, "detail": "NovelAI Token 验证成功，可以开始出图。"}
    if provider == "llm":
        token_value = payload.llm.token.strip() if payload and payload.llm.token else settings.llm_token
        endpoint_value = payload.llm.endpoint if payload and payload.llm.endpoint is not None else settings.llm_endpoint
        model_value = payload.llm.model.strip() if payload and payload.llm.model else settings.llm_model
        if not (token_value and endpoint_value and model_value):
            raise HTTPException(status_code=409, detail="未完整配置剧本文本模型")
        try:
            endpoint_value = settings.validate_endpoint(endpoint_value, "剧本文本接口")
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        models_url = _openai_models_url(endpoint_value)
        chat_url = _openai_chat_url(endpoint_value)
        token = token_value.removeprefix("Bearer ").strip()
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    models_url,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=f"剧本文本模型连接测试失败：{error}") from error
        if response.is_error:
            detail = response.text[:300].strip() or "上游未返回错误正文"
            raise HTTPException(status_code=response.status_code, detail=f"剧本文本模型连接测试失败（{models_url}）：{detail}")
        if _is_html_response(response):
            raise HTTPException(
                status_code=502,
                detail=(
                    "剧本文本接口返回了 HTML 网页，而不是 OpenAI JSON。"
                    f"测试地址：{models_url}。请填写 API Base URL（通常以 /v1 结尾），不要填写服务商网站首页。"
                ),
            )
        try:
            body = response.json()
        except ValueError as error:
            raise HTTPException(status_code=502, detail=f"剧本文本接口未返回 JSON（{models_url}）。") from error
        if not isinstance(body, dict):
            raise HTTPException(status_code=502, detail=f"剧本文本接口返回了非对象 JSON（{models_url}）。")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    chat_url,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                    json={
                        "model": model_value,
                        "messages": [
                            {"role": "system", "content": "Reply with exactly OK."},
                            {"role": "user", "content": "OK"},
                        ],
                        "temperature": 0,
                        "max_tokens": 8,
                    },
                )
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=f"剧本文本模型最小推理测试失败：{error}") from error
        if response.is_error:
            detail = response.text[:300].strip() or "上游未返回错误正文"
            raise HTTPException(status_code=response.status_code, detail=f"剧本文本模型最小推理测试失败（{chat_url}）：{detail}")
        if _is_html_response(response):
            raise HTTPException(
                status_code=502,
                detail=(
                    "剧本文本接口返回了 HTML 网页，而不是 OpenAI JSON。"
                    f"测试地址：{chat_url}。请填写 API Base URL（通常以 /v1 结尾），不要填写服务商网站首页。"
                ),
            )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise HTTPException(status_code=502, detail=f"剧本文本接口未返回 OpenAI Chat Completion JSON（{chat_url}）。") from error
        if not isinstance(content, str):
            raise HTTPException(status_code=502, detail=f"剧本文本接口返回了无效的 Chat Completion 内容（{chat_url}）。")
        return {"ok": True, "detail": f"剧本文本模型连接验证成功（模型列表与最小推理均通过）。"}
    raise HTTPException(status_code=404, detail="未知 Provider")


@router.post("/api/generate/image")
async def image(payload: ImageRequest):
    data, media_type = await generate_image(payload)
    return Response(content=data, media_type=media_type, headers={"Cache-Control":"no-store"})


@router.post("/api/assets/image")
async def save_image_asset(request: Request):
    """Persist a browser-generated image so a project survives a page reload."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    extensions = {"image/png": "png", "image/webp": "webp", "image/jpeg": "jpg"}
    extension = extensions.get(content_type)
    if extension is None:
        raise HTTPException(status_code=415, detail="仅支持保存 PNG、WEBP 或 JPEG 图片")
    content = await request.body()
    if not content:
        raise HTTPException(status_code=422, detail="图片内容为空")
    if len(content) > 40 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单张图片不能超过 40 MB")
    settings.assets_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    target = settings.assets_dir / filename
    temporary = target.with_suffix(f".{extension}.tmp")
    temporary.write_bytes(content)
    temporary.replace(target)
    return {"url": f"/api/assets/{filename}"}


@router.delete("/api/assets/{filename}")
async def delete_image_asset(filename: str):
    if not filename or Path(filename).name != filename or Path(filename).suffix.lower() not in {".png", ".webp", ".jpg"}:
        raise HTTPException(status_code=404, detail="素材不存在")
    target = settings.assets_dir / filename
    if not target.is_file():
        raise HTTPException(status_code=404, detail="素材不存在")
    target.unlink()
    return {"ok": True}


@router.get("/api/assets/{filename}")
async def read_image_asset(filename: str):
    # UUID filenames are generated by this server; forbid traversal and unknown extensions.
    if not filename or Path(filename).name != filename or Path(filename).suffix.lower() not in {".png", ".webp", ".jpg"}:
        raise HTTPException(status_code=404, detail="素材不存在")
    target = settings.assets_dir / filename
    if not target.is_file():
        raise HTTPException(status_code=404, detail="素材不存在")
    media_type = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg"}[target.suffix.lower()]
    return FileResponse(target, media_type=media_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.post("/api/resolve/characters")
async def resolve_character_names(payload: CharacterResolveRequest):
    return {"characters": await resolve_characters(payload.characters)}


@router.post("/api/generate/script")
async def script(payload: ScriptRequest):
    storyboard = await generate_storyboard(payload)
    if storyboard is None:
        return Response(status_code=204)
    return storyboard
