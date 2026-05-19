import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  createNewSessionId,
  getOrCreateGuestUserId,
  getOrCreateSessionId,
  resetGuestUser as createResetGuestUser,
} from "@/lib/guest-user";

export type BrowserLocation = {
  longitude: number;
  latitude: number;
};

export type LocationPermission =
  | "idle"
  | "requesting"
  | "granted"
  | "denied"
  | "error";

type UserState = {
  userId: string;
  sessionId: string;
  username: string;
  initialized: boolean;
  currentLocation: BrowserLocation | null;
  locationLabel: string | null;
  locationPermission: LocationPermission;
  initGuestUser: () => void;
  newSession: () => void;
  resetGuestUser: () => void;
  setUser: (user: {
    userId?: string;
    sessionId?: string;
    username?: string;
  }) => void;
  setCurrentLocation: (location: BrowserLocation, label?: string) => void;
  clearCurrentLocation: () => void;
  setLocationPermission: (status: LocationPermission) => void;
};

const defaultUserId =
  process.env.NEXT_PUBLIC_DEFAULT_USER_ID ?? "guest_pending";
const defaultSessionId =
  process.env.NEXT_PUBLIC_DEFAULT_SESSION_ID ?? "session_pending";

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      userId: defaultUserId,
      sessionId: defaultSessionId,
      username: "匿名用户",
      initialized: false,
      currentLocation: null,
      locationLabel: null,
      locationPermission: "idle",
      initGuestUser: () => {
        const userId = getOrCreateGuestUserId();
        const sessionId = getOrCreateSessionId();
        set({
          userId,
          sessionId,
          username: "匿名用户",
          initialized: true,
        });
      },
      newSession: () =>
        set({
          sessionId: createNewSessionId(),
        }),
      resetGuestUser: () => {
        const userId = createResetGuestUser();
        const sessionId = createNewSessionId();
        set({
          userId,
          sessionId,
          username: "匿名用户",
          currentLocation: null,
          locationLabel: null,
          locationPermission: "idle",
          initialized: true,
        });
      },
      setUser: (user) =>
        set((state) => ({
          userId: user.userId ?? state.userId,
          sessionId: user.sessionId ?? state.sessionId,
          username: user.username ?? state.username,
        })),
      setCurrentLocation: (location, label = "当前位置") =>
        set({
          currentLocation: location,
          locationLabel: label,
          locationPermission: "granted",
        }),
      clearCurrentLocation: () =>
        set({
          currentLocation: null,
          locationLabel: null,
          locationPermission: "idle",
        }),
      setLocationPermission: (status) =>
        set({
          locationPermission: status,
        }),
    }),
    {
      name: "tastescout-user-state",
      version: 2,
    },
  ),
);
