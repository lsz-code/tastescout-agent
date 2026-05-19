"use client";

import { useState } from "react";
import { BrowserLocation } from "@/stores/user-store";

type BrowserLocationError = {
  message: string;
};

export function useBrowserLocation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function requestLocation(): Promise<BrowserLocation | null> {
    setError(null);

    if (typeof navigator === "undefined" || !navigator.geolocation) {
      const message = "当前浏览器不支持定位功能。";
      setError(message);
      throw { message } satisfies BrowserLocationError;
    }

    setLoading(true);

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location = {
            longitude: position.coords.longitude,
            latitude: position.coords.latitude,
          };
          setLoading(false);
          setError(null);
          resolve(location);
        },
        (geoError) => {
          const message = getLocationErrorMessage(geoError);
          setLoading(false);
          setError(message);
          reject({ message } satisfies BrowserLocationError);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000,
        },
      );
    });
  }

  return {
    loading,
    error,
    requestLocation,
  };
}

function getLocationErrorMessage(error: GeolocationPositionError) {
  if (error.code === error.PERMISSION_DENIED) {
    return "你拒绝了定位权限，请在浏览器设置中允许定位。";
  }
  if (error.code === error.POSITION_UNAVAILABLE) {
    return "暂时无法获取当前位置。";
  }
  if (error.code === error.TIMEOUT) {
    return "定位超时，请稍后重试。";
  }
  return "定位失败，请稍后重试。";
}
