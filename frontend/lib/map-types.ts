export type MapRestaurantMarker = {
  poi_id: string;
  name: string;
  longitude: number;
  latitude: number;
  address?: string | null;
  rating?: number | null;
  avg_price?: number | null;
  distance?: number | null;
  score?: number | null;
  rank?: number;
  cuisine_type?: string | null;
};
