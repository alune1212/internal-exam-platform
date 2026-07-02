import { FileSpreadsheet, FileUp } from "lucide-react";
import type { ReactNode } from "react";
import { useRef } from "react";

import { PageSection } from "@/components/page";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

interface ImportPanelProps {
  fileInputId: string;
  fileLabel: string;
  selectedFile: File | null;
  accept?: string;
  intro?: ReactNode;
  templateAction?: ReactNode;
  children?: ReactNode;
  uploadLabel: string;
  pendingLabel: string;
  pendingAriaLabel: string;
  fileDisabled?: boolean;
  uploadDisabled?: boolean;
  isPending: boolean;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
}

export function ImportPanel({
  fileInputId,
  fileLabel,
  selectedFile,
  accept = ".xlsx,.xls",
  intro,
  templateAction,
  children,
  uploadLabel,
  pendingLabel,
  pendingAriaLabel,
  fileDisabled = false,
  uploadDisabled = false,
  isPending,
  onFileChange,
  onUpload,
}: ImportPanelProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <PageSection variant="panel" className="rounded-lg p-6 lg:p-8">
      {intro}

      {templateAction ? (
        <div className="flex flex-wrap items-center gap-3">{templateAction}</div>
      ) : null}

      <FieldGroup>
        <Field>
          <FieldLabel htmlFor={fileInputId}>{fileLabel}</FieldLabel>
          <input
            ref={fileInputRef}
            id={fileInputId}
            type="file"
            accept={accept}
            disabled={fileDisabled}
            className="sr-only"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
          <div className="flex flex-col gap-3 rounded-md border border-hairline bg-canvas p-3 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <p
                className={cn(
                  "truncate text-body-sm font-medium",
                  selectedFile ? "text-ink" : "text-muted",
                )}
              >
                {selectedFile?.name ?? "未选择文件"}
              </p>
              <p className="text-caption uppercase tracking-[0.16em] text-muted">
                Excel .xlsx / .xls
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="self-start md:self-auto"
              disabled={fileDisabled}
              onClick={() => fileInputRef.current?.click()}
            >
              <FileSpreadsheet data-icon="inline-start" />
              选择文件
            </Button>
          </div>
        </Field>
      </FieldGroup>

      <Button
        type="button"
        size="lg"
        className="self-start"
        disabled={!selectedFile || isPending || fileDisabled || uploadDisabled}
        onClick={onUpload}
      >
        {isPending ? (
          <Spinner data-icon="inline-start" aria-label={pendingAriaLabel} />
        ) : (
          <FileUp data-icon="inline-start" />
        )}
        {isPending ? pendingLabel : uploadLabel}
      </Button>

      {children}
    </PageSection>
  );
}
