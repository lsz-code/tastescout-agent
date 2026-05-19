"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapPin } from "lucide-react";
import { RestaurantItem } from "@/lib/api-types";
import { MapRestaurantMarker } from "@/lib/map-types";

type RestaurantMapProps = {
  restaurants: RestaurantItem[];
  userLocation?: {
    longitude: number;
    latitude: number;
  } | null;
  selectedPoiId?: string | null;
  onSelectRestaurant?: (poiId: string) => void;
};

type MarkerRecord = {
  poiId: string;
  marker: any;
  data: MapRestaurantMarker;
};

const BEIJING_CENTER = {
  longitude: 116.397428,
  latitude: 39.90923,
};

function parseCoordinate(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function parseRestaurantLocation(restaurant: RestaurantItem) {
  const location = restaurant.location;
  if (typeof location === "string") {
    const [longitudeText, latitudeText] = location.split(",");
    const longitude = parseCoordinate(longitudeText);
    const latitude = parseCoordinate(latitudeText);
    if (longitude != null && latitude != null) {
      return { longitude, latitude };
    }
  }

  if (location && typeof location === "object") {
    const record = location as Record<string, unknown>;
    const longitude = parseCoordinate(record.longitude ?? record.lng);
    const latitude = parseCoordinate(record.latitude ?? record.lat);
    if (longitude != null && latitude != null) {
      return { longitude, latitude };
    }
  }

  return null;
}

function toMapMarkers(restaurants: RestaurantItem[]): MapRestaurantMarker[] {
  const markerItems: MapRestaurantMarker[] = [];

  restaurants.forEach((restaurant) => {
    const coordinate = parseRestaurantLocation(restaurant);
    if (!coordinate) return;

    markerItems.push({
      poi_id: restaurant.poi_id,
      name: restaurant.name,
      longitude: coordinate.longitude,
      latitude: coordinate.latitude,
      address: restaurant.address,
      rating: restaurant.rating,
      avg_price: restaurant.avg_price,
      distance: restaurant.distance,
      score: restaurant.score,
      rank: restaurant.rank,
      cuisine_type: restaurant.cuisine_type,
    });
  });

  return markerItems;
}

function formatDistance(distance?: number | null) {
  if (distance == null) return "距离未知";
  if (distance >= 1000) return `距离 ${(distance / 1000).toFixed(1)}km`;
  return `距离 ${Math.round(distance)}m`;
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function createRestaurantMarkerContent(rank?: number, selected?: boolean) {
  return `
    <div style="
      width: 32px;
      height: 32px;
      border-radius: 999px;
      background: ${selected ? "#111111" : "#ffffff"};
      color: ${selected ? "#ffffff" : "#111111"};
      border: 2px solid #111111;
      box-shadow: 0 10px 24px rgba(0,0,0,0.18);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">${rank ?? ""}</div>
  `;
}

function createUserMarkerContent() {
  return `
    <div style="
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      background: #111111;
      color: #ffffff;
      padding: 7px 10px;
      box-shadow: 0 10px 24px rgba(0,0,0,0.18);
      white-space: nowrap;
      font-size: 12px;
      font-weight: 600;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    ">
      <span style="width: 8px; height: 8px; border-radius: 999px; background: #ffffff;"></span>
      我在这里
    </div>
  `;
}

function createInfoWindowContent(restaurant: MapRestaurantMarker) {
  const rating = restaurant.rating != null ? `评分 ${restaurant.rating}` : "暂无评分";
  const price =
    restaurant.avg_price != null ? `人均 ¥${Math.round(restaurant.avg_price)}` : "价格未知";
  const distance = formatDistance(restaurant.distance);
  const address = restaurant.address ?? "暂无地址";
  const nameText = escapeHtml(restaurant.name);
  const addressText = escapeHtml(address);

  return `
    <div style="
      min-width: 220px;
      max-width: 280px;
      padding: 4px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #111111;
    ">
      <div style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">${nameText}</div>
      <div style="display: grid; gap: 5px; color: #555555; font-size: 12px; line-height: 1.5;">
        <div>${rating}</div>
        <div>${price}</div>
        <div>${distance}</div>
        <div>${addressText}</div>
      </div>
    </div>
  `;
}

export function RestaurantMap({
  restaurants,
  userLocation,
  selectedPoiId,
  onSelectRestaurant,
}: RestaurantMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const amapRef = useRef<any>(null);
  const markerRecordsRef = useRef<MarkerRecord[]>([]);
  const userMarkerRef = useRef<any>(null);
  const infoWindowRef = useRef<any>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const amapKey = process.env.NEXT_PUBLIC_AMAP_JS_KEY;
  const markers = useMemo(() => toMapMarkers(restaurants), [restaurants]);
  const hasRestaurants = restaurants.length > 0;
  const hasMappableRestaurants = markers.length > 0;

  const defaultCenter = useMemo(() => {
    if (userLocation) return userLocation;
    if (markers[0]) {
      return {
        longitude: markers[0].longitude,
        latitude: markers[0].latitude,
      };
    }
    return BEIJING_CENTER;
  }, [markers, userLocation]);

  useEffect(() => {
    if (!amapKey || !containerRef.current || mapRef.current) return;

    let cancelled = false;

    import("@amap/amap-jsapi-loader")
      .then(({ default: AMapLoader }) =>
        AMapLoader.load({
          key: amapKey,
          version: "2.0",
        }),
      )
      .then((AMap) => {
        if (cancelled || !containerRef.current) return;
        amapRef.current = AMap;
        mapRef.current = new AMap.Map(containerRef.current, {
          center: [defaultCenter.longitude, defaultCenter.latitude],
          zoom: 13,
          resizeEnable: true,
        });
        infoWindowRef.current = new AMap.InfoWindow({
          offset: new AMap.Pixel(0, -30),
          isCustom: false,
        });
        setMapReady(true);
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError("地图加载失败，请检查高德地图 Key 是否正确。");
        }
      });

    return () => {
      cancelled = true;
      markerRecordsRef.current = [];
      userMarkerRef.current = null;
      infoWindowRef.current = null;
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
      amapRef.current = null;
    };
  }, [amapKey, defaultCenter.latitude, defaultCenter.longitude]);

  useEffect(() => {
    const AMap = amapRef.current;
    const map = mapRef.current;
    if (!AMap || !map || !mapReady) return;

    markerRecordsRef.current.forEach(({ marker }) => {
      map.remove(marker);
    });
    markerRecordsRef.current = [];

    if (userMarkerRef.current) {
      map.remove(userMarkerRef.current);
      userMarkerRef.current = null;
    }

    const fitTargets: any[] = [];

    if (userLocation) {
      const userMarker = new AMap.Marker({
        position: [userLocation.longitude, userLocation.latitude],
        content: createUserMarkerContent(),
        anchor: "bottom-center",
        zIndex: 120,
      });
      map.add(userMarker);
      userMarkerRef.current = userMarker;
      fitTargets.push(userMarker);
    }

    markers.forEach((restaurant) => {
      const marker = new AMap.Marker({
        position: [restaurant.longitude, restaurant.latitude],
        content: createRestaurantMarkerContent(restaurant.rank),
        anchor: "center",
        zIndex: 100,
      });

      marker.on("click", () => {
        onSelectRestaurant?.(restaurant.poi_id);
        infoWindowRef.current?.setContent(createInfoWindowContent(restaurant));
        infoWindowRef.current?.open(map, [restaurant.longitude, restaurant.latitude]);
      });

      map.add(marker);
      markerRecordsRef.current.push({
        poiId: restaurant.poi_id,
        marker,
        data: restaurant,
      });
      fitTargets.push(marker);
    });

    if (fitTargets.length > 0) {
      map.setFitView(fitTargets, false, [56, 36, 56, 36]);
    } else {
      map.setCenter([defaultCenter.longitude, defaultCenter.latitude]);
    }
  }, [
    defaultCenter.latitude,
    defaultCenter.longitude,
    mapReady,
    markers,
    onSelectRestaurant,
    userLocation,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedPoiId) return;

    const selected = markerRecordsRef.current.find(
      (record) => record.poiId === selectedPoiId,
    );
    if (!selected) return;

    markerRecordsRef.current.forEach((record) => {
      record.marker.setContent(
        createRestaurantMarkerContent(
          record.data.rank,
          record.poiId === selectedPoiId,
        ),
      );
      record.marker.setzIndex?.(record.poiId === selectedPoiId ? 110 : 100);
    });

    const position = [selected.data.longitude, selected.data.latitude];
    map.panTo(position);
    infoWindowRef.current?.setContent(createInfoWindowContent(selected.data));
    infoWindowRef.current?.open(map, position);
  }, [selectedPoiId]);

  if (!amapKey) {
    return (
      <MapPlaceholder text="未配置高德地图 Key，暂时无法显示地图。" />
    );
  }

  if (!hasRestaurants) {
    return (
      <MapPlaceholder text="推荐结果出现后，会在这里显示餐厅位置。" />
    );
  }

  if (!hasMappableRestaurants) {
    return (
      <MapPlaceholder text="当前推荐结果缺少坐标，暂时无法在地图上展示。" />
    );
  }

  if (loadError) {
    return <MapPlaceholder text={loadError} />;
  }

  return (
    <div
      ref={containerRef}
      className="h-full min-h-[360px] w-full overflow-hidden rounded-2xl border border-border bg-neutral-100"
    />
  );
}

function MapPlaceholder({ text }: { text: string }) {
  return (
    <div className="flex h-full min-h-[360px] w-full items-center justify-center rounded-2xl border border-border bg-neutral-50 px-6 text-center text-sm leading-6 text-muted-foreground">
      <div>
        <MapPin className="mx-auto mb-3 h-6 w-6 text-neutral-500" />
        {text}
      </div>
    </div>
  );
}
