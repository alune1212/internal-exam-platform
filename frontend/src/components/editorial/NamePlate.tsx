import * as React from "react";

import { pickPastel } from "@/lib/pastelPalette";
import { cn } from "@/lib/utils";

export interface NamePlateCandidate {
  displayName?: string;
  subtitle?: string;
}

export interface NamePlateProps extends React.HTMLAttributes<HTMLDivElement> {
  name?: string;
  subtitle?: string;
  candidate?: NamePlateCandidate;
  avatarSize?: number;
}

export function NamePlate({
  name,
  subtitle,
  candidate,
  avatarSize = 24,
  className,
  ...props
}: NamePlateProps) {
  const displayName = name ?? candidate?.displayName ?? "";
  const displaySubtitle = subtitle ?? candidate?.subtitle;
  const initial = (displayName.trim().charAt(0) || "?").toUpperCase();
  const avatarBg = pickPastel(displayName);

  return (
    <div className={cn("inline-flex min-w-0 items-center gap-2", className)} {...props}>
      <span
        aria-hidden="true"
        className="inline-flex shrink-0 items-center justify-center rounded-full font-display text-caption font-semibold text-ink"
        style={{
          width: `${avatarSize}px`,
          height: `${avatarSize}px`,
          backgroundColor: avatarBg,
        }}
      >
        {initial}
      </span>
      <span className="flex min-w-0 flex-col leading-tight">
        <span className="break-words font-display text-body-sm font-semibold text-ink">
          {displayName}
        </span>
        {displaySubtitle ? (
          <span className="break-words text-caption text-muted">{displaySubtitle}</span>
        ) : null}
      </span>
    </div>
  );
}
