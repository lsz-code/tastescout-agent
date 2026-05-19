import {
  AddFavoriteRequest,
  AddFavoriteResponse,
  AgentChatRequest,
  AgentChatResponse,
  FavoriteRestaurant,
  LongTermMemoryResponse,
} from "@/lib/api-types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = await response.json();
      message =
        typeof payload.detail === "string"
          ? payload.detail
          : JSON.stringify(payload);
    } catch {
      message = await response.text();
    }
    throw new ApiError(
      response.status,
      message || "请求失败，请检查后端服务是否正常运行。",
    );
  }

  return response.json() as Promise<T>;
}

export function bootstrapUser(userId: string, username?: string) {
  return request("/users/bootstrap", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      username: username ?? userId,
    }),
  });
}

export function sendAgentMessage(payload: AgentChatRequest) {
  return request<AgentChatResponse>("/agent/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getShortTermMemory(sessionId: string) {
  return request<Record<string, unknown>>(`/memory/short-term/${sessionId}`);
}

export function getLongTermMemory(userId: string) {
  return request<LongTermMemoryResponse>(`/memory/long-term/${userId}`);
}

export function addFavorite(payload: AddFavoriteRequest) {
  return request<AddFavoriteResponse>("/favorites", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFavorites(userId: string): Promise<FavoriteRestaurant[]> {
  const params = new URLSearchParams({ user_id: userId });
  return request<FavoriteRestaurant[]>(`/favorites?${params.toString()}`);
}

export function refreshLongTermMemory(userId: string) {
  return request(`/memory/long-term/${userId}/refresh`, {
    method: "POST",
  });
}
