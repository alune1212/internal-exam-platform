import { apiRequest } from "@/api/client";
import type { OperationsSnapshot } from "@/types/operations";

export function getOperationsSnapshot() {
  return apiRequest<OperationsSnapshot>("/api/admin/operations/snapshot");
}
