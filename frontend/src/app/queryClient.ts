import { QueryClient } from "@tanstack/react-query";

import { subscribeSessionChanges } from "@/lib/sessionEvents";

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
  return subscribeSessionChanges(() => {
    queryClient.clear();
  });
}
