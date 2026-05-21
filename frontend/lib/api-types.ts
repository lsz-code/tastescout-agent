export type AgentChatRequest = {
  user_id: string;
  session_id: string;
  message: string;
  location?: {
    longitude: number;
    latitude: number;
  } | null;
  location_label?: string | null;
};

export type AgentToolCall = {
  tool_name: string;
  arguments?: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  success: boolean;
  error?: string | null;
};

export type RestaurantItem = {
  rank: number;
  poi_id: string;
  name: string;
  address?: string | null;
  photo?: string | null;
  location?: Record<string, unknown> | string | null;
  cuisine_type?: string | null;
  rating?: number | null;
  avg_price?: number | null;
  distance?: number | null;
  score?: number | null;
  match_reasons?: string[];
  recommend_reason?: string | null;
  recommended_dishes?: unknown[] | null;
  review_summary?: string | null;
  raw_data?: Record<string, unknown> | null;
};

export type ReviewItem = {
  id: number;
  restaurant_id: number;
  user_id: string;
  username?: string | null;
  content: string;
  rating?: number | null;
  created_at: string;
  updated_at: string;
};

export type RestaurantDetail = {
  id: number;
  poi_id: string;
  name: string;
  address?: string | null;
  photo?: string | null;
  location?: Record<string, unknown> | string | null;
  cuisine_type?: string | null;
  rating?: number | null;
  avg_price?: number | null;
  raw_data?: Record<string, unknown> | null;
  reviews: ReviewItem[];
  created_at: string;
  updated_at: string;
};

export type UpsertRestaurantRequest = {
  poi_id: string;
  name: string;
  address?: string | null;
  photo?: string | null;
  location?: Record<string, unknown> | string | null;
  cuisine_type?: string | null;
  rating?: number | null;
  avg_price?: number | null;
  raw_data?: Record<string, unknown> | null;
};

export type CreateReviewRequest = {
  user_id: string;
  content: string;
  rating?: number | null;
};

export type AgentChatResponse = {
  user_id: string;
  session_id: string;
  reply: string;
  intent?: string | null;
  tool_calls: AgentToolCall[];
  data?: {
    restaurants?: RestaurantItem[];
    [key: string]: unknown;
  } | null;
  memory_used: boolean;
};

export type FavoriteRestaurant = {
  id: number;
  collection_id: number;
  poi_id: string;
  name: string;
  address?: string | null;
  photo?: string | null;
  cuisine_type?: string | null;
  rating?: number | null;
  avg_price?: number | null;
  distance?: number | null;
  recommended_dishes?: unknown[] | null;
  review_summary?: string | null;
  recommend_reason?: string | null;
  created_at?: string;
};

export type FavoriteCollection = {
  id: number;
  user_id: number;
  name: string;
  description?: string | null;
  is_default: boolean;
  restaurant_count: number;
};

export type CreateFavoriteCollectionRequest = {
  user_id: string;
  name: string;
  description?: string | null;
};

export type CreateFavoriteCollectionResponse = FavoriteCollection;

export type AddFavoriteRequest = {
  user_id: string;
  collection_id?: number | null;
  poi_id: string;
  name: string;
  address?: string | null;
  photo?: string | null;
  location?: Record<string, unknown> | string | null;
  cuisine_type?: string | null;
  rating?: number | null;
  avg_price?: number | null;
  distance?: number | null;
  recommended_dishes?: unknown[] | null;
  review_summary?: string | null;
  recommend_reason?: string | null;
  raw_data?: Record<string, unknown> | null;
};

export type AddFavoriteResponse = {
  success: boolean;
  already_exists: boolean;
  favorite_id?: number | null;
  message: string;
};

export type LongTermMemoryResponse = {
  user_id: string;
  memory?: {
    favorite_cuisines?: string[];
    taste_preference?: string[];
    avoid_foods?: string[];
    favorite_dishes?: string[];
    preferred_scenes?: string[];
    price_preference?: {
      min_price?: number | null;
      max_price?: number | null;
      avg_price?: number | null;
    };
    memory_summary?: string;
    [key: string]: unknown;
  } | null;
  updated_at?: string | null;
};
