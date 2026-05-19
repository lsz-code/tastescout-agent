import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel

from config import settings


app = FastAPI(title="Amap MCP Proxy")


class GeocodeRequest(BaseModel):
    address: str
    city: str | None = None


class TextSearchRequest(BaseModel):
    keywords: str
    city: str | None = None


class Location(BaseModel):
    longitude: float
    latitude: float


class AroundSearchRequest(BaseModel):
    location: Location
    keywords: str = "美食"
    radius: int = 3000


class PlaceDetailRequest(BaseModel):
    poi_id: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

#调用高德MCP，列出工具
@app.get("/tools")
async def tools() -> list[dict[str, Any]]:
    try:
        async with asyncio.timeout(settings.MCP_TIMEOUT_SECONDS):
            async with streamable_http_client(settings.AMAP_MCP_URL) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="MCP list_tools timed out") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MCP list_tools failed: {exc}") from exc

    return [_to_plain_dict(tool) for tool in getattr(result, "tools", result)]

#地址解码为经纬度
@app.post("/geocode")
async def geocode(payload: GeocodeRequest) -> dict[str, Any]:
    arguments: dict[str, Any] = {"address": payload.address}
    if payload.city is not None:
        arguments["city"] = payload.city
    return await _call_tool("maps_geo", arguments)

#按文本搜索周边餐厅
@app.post("/text-search")
async def text_search(payload: TextSearchRequest) -> dict[str, Any]:
    arguments: dict[str, Any] = {"keywords": payload.keywords}
    if payload.city is not None:
        arguments["city"] = payload.city
    return await _call_tool("maps_text_search", arguments)


@app.post("/around-search")
async def around_search(payload: AroundSearchRequest) -> dict[str, Any]:
    return await _call_tool(
        "maps_around_search",
        {
            "location": f"{payload.location.longitude},{payload.location.latitude}",
            "keywords": payload.keywords,
            "radius": payload.radius,
        },
    )


@app.post("/place-detail")
async def place_detail(payload: PlaceDetailRequest) -> dict[str, Any]:
    return await _call_tool("maps_search_detail", {"id": payload.poi_id})

#工具调用统一封装，使用AMAP_MCP_URL通过streamable_http_client调用高德MCP工具
#根据工具名称和参数调用工具，并处理超时、HTTP错误、以及工具返回的错误信息
async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        async with asyncio.timeout(settings.MCP_TIMEOUT_SECONDS):
            async with streamable_http_client(settings.AMAP_MCP_URL) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=f"MCP call timed out: {tool_name}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"MCP call failed: {tool_name}: {exc}",
        ) from exc

    text = _extract_text(result)
    is_error = bool(getattr(result, "isError", False))

    if text is None:
        payload = _to_plain_dict(result)
        if is_error:
            raise HTTPException(status_code=502, detail=payload)
        return payload

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if is_error:
            raise HTTPException(status_code=502, detail=text)
        return {"raw_text": text}

    if is_error:
        raise HTTPException(status_code=502, detail=payload)

    if not isinstance(payload, dict):
        return {"data": payload}

    return payload


def _extract_text(result: Any) -> str | None:
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text is not None:
            return text

        if isinstance(item, dict) and item.get("type") == "text":
            return item.get("text")

    return None


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}
