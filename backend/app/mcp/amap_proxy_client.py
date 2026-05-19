from typing import Any

import httpx

#高德地图MCP代理客户端类
class AmapProxyClient:
    def __init__(self, proxy_url: str, timeout_seconds: int = 15) -> None:
        if not proxy_url:
            raise RuntimeError("AMAP_MCP_PROXY_URL is required")

        self.proxy_url = proxy_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    #列出工具列表
    async def list_tools(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/tools")
        if not isinstance(payload, list):
            raise RuntimeError("Amap MCP proxy returned invalid tools response")
        return payload

    #根据地址解析经纬度坐标
    async def geocode(self, address: str, city: str | None = None) -> dict[str, Any]:
        data: dict[str, Any] = {"address": address}
        if city is not None:
            data["city"] = city
        return await self._request("POST", "/geocode", json=data)

    #根据地址和关键词搜索餐厅
    async def text_search(
        self,
        keywords: str,
        city: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"keywords": keywords}
        if city is not None:
            data["city"] = city
        return await self._request("POST", "/text-search", json=data)

    #根据经纬度搜索餐厅
    async def around_search(
        self,
        location: dict[str, Any],
        keywords: str = "美食",
        radius: int = 3000,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/around-search",
            json={
                "location": location,
                "keywords": keywords,
                "radius": radius,
            },
        )

    #根据餐厅唯一ID获取餐厅详情
    async def place_detail(self, poi_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/place-detail",
            json={"poi_id": poi_id},
        )

    #发送HTTP请求到MCP代理，并处理响应和错误
    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            base_url=self.proxy_url,
            timeout=timeout,
        ) as client:
            try:
                response = await client.request(method, path, json=json)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                raise RuntimeError(
                    f"Amap MCP proxy returned HTTP {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Amap MCP proxy request failed: {exc}") from exc

        return response.json()
