import { cn } from "@/lib/utils";

type MetricTone = "default" | "success" | "warning";

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  tone?: MetricTone;
  caption?: string;
}

const TONE_CLASS: Record<MetricTone, string> = {
  default: "text-ink",
  success: "text-success",
  warning: "text-warning",
};

export function MetricCard({ label, value, unit, tone = "default", caption }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-hairline bg-canvas p-[18px] shadow-card">
      <p className="font-body text-caption font-medium uppercase tracking-[0.16em] text-muted">
        {label}
      </p>
      <p className="mt-3 flex items-baseline gap-1 font-display text-[32px] font-semibold leading-none tracking-[-0.04em] lg:text-[40px]">
        <span className={cn(TONE_CLASS[tone])}>{value}</span>
        {unit ? <span className="text-base text-muted">{unit}</span> : null}
      </p>
      {caption ? <p className="mt-3 text-caption text-muted">{caption}</p> : null}
    </div>
  );
}
