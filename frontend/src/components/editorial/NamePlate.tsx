import * as React from "react";

import { pickPastel } from "@/lib/pastelPalette";
import { cn } from "@/lib/utils";

export interface NamePlateCandidate {
  name: string;
  employeeNo?: string;
  department?: string;
}

export interface NamePlateProps extends React.HTMLAttributes<HTMLDivElement> {
  name?: string;
  subtitle?: string;
  candidate?: NamePlateCandidate;
  avatarSize?: number;
}

function buildCandidateSubtitle(candidate: NamePlateCandidate | undefined) {
  if (!candidate) return undefined;

  return [candidate.employeeNo, candidate.department].filter(Boolean).join(" · ") || undefined;
}

export function NamePlate({
  name,
  subtitle,
  candidate,
  avatarSize = 24,
  className,
  ...props
}: NamePlateProps) {
  const displayName = name ?? candidate?.name ?? "";
  const displaySubtitle = subtitle ?? buildCandidateSubtitle(candidate);
  const initial = (displayName.trim().charAt(0) || "?").toUpperCase();
  const avatarBg = pickPastel(displayName);

  return (
    <div className={cn("inline-flex items-center gap-2", className)} {...props}>
      <span
        aria-hidden="true"
        className="inline-flex shrink-0 items-center justify-center rounded-full font-display text-[12px] font-semibold text-ink"
        style={{
          width: `${avatarSize}px`,
          height: `${avatarSize}px`,
          backgroundColor: avatarBg,
        }}
      >
        {initial}
      </span>
      <span className="flex flex-col leading-tight">
        <span className="font-display text-[14px] font-semibold text-ink">{displayName}</span>
        {displaySubtitle ? (
          <span className="text-[11px] italic text-muted">{displaySubtitle}</span>
        ) : null}
      </span>
    </div>
  );
}
