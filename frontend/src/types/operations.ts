export type OperationalSignalStatus =
  | "loading"
  | "current"
  | "degraded"
  | "stale"
  | "skipped"
  | "failed";

export type OperationalSignal = {
  status: OperationalSignalStatus;
  summary: string;
  checked_at: string;
  details: Record<string, unknown>;
};

export type OperationsSnapshot = {
  checked_at: string;
  version: OperationalSignal;
  migration: OperationalSignal;
  service_health: OperationalSignal;
  worker_health: OperationalSignal;
  operational_lock: OperationalSignal;
  disk_reserve: OperationalSignal;
  backup: OperationalSignal;
  second_copy: OperationalSignal;
  restore_drill: OperationalSignal;
  retention: OperationalSignal;
  security_scan: OperationalSignal;
};
