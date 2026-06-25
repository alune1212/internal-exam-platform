export type SessionChangeReason =
  | "candidate-login"
  | "candidate-logout"
  | "admin-login"
  | "admin-logout"
  | "unauthorized";

export type SessionChangeEvent = {
  reason: SessionChangeReason;
};

const sessionTarget = new EventTarget();
const SESSION_CHANGED = "internal-exam-session-changed";

export function emitSessionChanged(detail: SessionChangeEvent): void {
  sessionTarget.dispatchEvent(new CustomEvent(SESSION_CHANGED, { detail }));
}

export function subscribeSessionChanges(listener: (event: SessionChangeEvent) => void): () => void {
  const wrapped = (event: Event) => {
    listener((event as CustomEvent<SessionChangeEvent>).detail);
  };
  sessionTarget.addEventListener(SESSION_CHANGED, wrapped);
  return () => sessionTarget.removeEventListener(SESSION_CHANGED, wrapped);
}
