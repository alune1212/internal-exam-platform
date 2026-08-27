import { QueryClient } from "@tanstack/react-query";

export type SessionChangeReason =
  | "candidate-login"
  | "candidate-logout"
  | "admin-login"
  | "admin-logout"
  | "unauthorized";

const sessionChangeListeners = new Set<(reason: SessionChangeReason) => void>();

export function subscribeSessionChange(
  listener: (reason: SessionChangeReason) => void,
): () => void {
  sessionChangeListeners.add(listener);
  return () => {
    sessionChangeListeners.delete(listener);
  };
}

export function emitSessionChange(reason: SessionChangeReason): void {
  sessionChangeListeners.forEach((listener) => listener(reason));
}

export function createAppQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export function bindSessionCacheClearing(queryClient: QueryClient): () => void {
  return subscribeSessionChange(() => {
    queryClient.clear();
  });
}
