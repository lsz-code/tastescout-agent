const GUEST_USER_KEY = "tastescout_guest_user_id";
const SESSION_KEY = "tastescout_current_session_id";

function canUseBrowserStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function randomSegment() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replace(/-/g, "").slice(0, 8);
  }
  return Math.random().toString(36).slice(2, 10);
}

function createGuestUserId() {
  return `guest_${randomSegment()}`;
}

function createSessionId() {
  return `session_${randomSegment()}`;
}

export function getOrCreateGuestUserId(): string {
  if (!canUseBrowserStorage()) {
    return process.env.NEXT_PUBLIC_DEFAULT_USER_ID ?? "guest_fallback";
  }

  const existing = window.localStorage.getItem(GUEST_USER_KEY);
  if (existing) return existing;

  const userId = createGuestUserId();
  window.localStorage.setItem(GUEST_USER_KEY, userId);
  return userId;
}

export function getOrCreateSessionId(): string {
  if (!canUseBrowserStorage()) {
    return process.env.NEXT_PUBLIC_DEFAULT_SESSION_ID ?? "session_fallback";
  }

  const existing = window.localStorage.getItem(SESSION_KEY);
  if (existing) return existing;

  const sessionId = createSessionId();
  window.localStorage.setItem(SESSION_KEY, sessionId);
  return sessionId;
}

export function createNewSessionId(): string {
  const sessionId = createSessionId();
  if (canUseBrowserStorage()) {
    window.localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

export function resetGuestUser(): string {
  const userId = createGuestUserId();
  if (canUseBrowserStorage()) {
    window.localStorage.setItem(GUEST_USER_KEY, userId);
    window.localStorage.removeItem(SESSION_KEY);
  }
  return userId;
}
