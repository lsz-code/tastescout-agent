from fastapi import APIRouter, HTTPException

from app.mcp.schemas import (
    AroundSearchRequest,
    GeocodeRequest,
    GeocodeResponse,
    PlaceDetailRequest,
    PlaceDetailResponse,
    SearchResponse,
    TextSearchRequest,
)
from app.services.mcp_service import MCPService


router = APIRouter(prefix="/mcp", tags=["MCP"])

#MCP工具，列出工具列表
@router.get("/tools")
async def list_tools() -> list[dict]:
    try:
        service = MCPService()
        return await service.list_tools()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

#MCP工具，根据地址解析经纬度
@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(payload: GeocodeRequest) -> GeocodeResponse:
    try:
        service = MCPService()
        return await service.geocode(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

#MCP工具，根据关键词和地址搜索餐厅
@router.post("/text-search", response_model=SearchResponse)
async def text_search(payload: TextSearchRequest) -> SearchResponse:
    try:
        service = MCPService()
        return await service.text_search(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

#MCP工具，根据经纬度搜索餐厅
@router.post("/around-search", response_model=SearchResponse)
async def around_search(payload: AroundSearchRequest) -> SearchResponse:
    try:
        service = MCPService()
        return await service.around_search(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

#MCP工具，根据餐厅唯一ID获取餐厅详情
@router.post("/place-detail", response_model=PlaceDetailResponse)
async def place_detail(payload: PlaceDetailRequest) -> PlaceDetailResponse:
    try:
        service = MCPService()
        return await service.place_detail(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
