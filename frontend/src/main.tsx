import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { bindSessionCacheClearing, createAppQueryClient } from "@/app/queryClient";
import { router } from "@/app/router";
import "@/index.css";

const queryClient = createAppQueryClient();
bindSessionCacheClearing(queryClient);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
