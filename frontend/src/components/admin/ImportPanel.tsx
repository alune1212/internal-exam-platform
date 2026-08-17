import { FileSpreadsheet, FileUp } from "lucide-react";
import type { ReactNode } from "react";
import { useRef } from "react";

import { PageActions, PageSection } from "@/components/page";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Spinner } from "@/components/ui/spinner";
import { importCopy } from "@/lib/pageCopy";
import { cn } from "@/lib/utils";

export interface ImportPanelProps {
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
    <PageSection
      variant="panel"
      data-testid="import-panel"
      data-import-state={isPending ? "pending" : selectedFile ? "ready" : "idle"}
    >
      {intro}

      {templateAction ? (
        <PageActions placement="card" aria-label="模板操作">
          {templateAction}
        </PageActions>
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
            aria-busy={isPending}
            className="sr-only"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
          <div className="flex flex-col gap-3 border-t border-hairline-soft pt-3 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <p
                className={cn(
                  "truncate text-body-sm font-medium",
                  selectedFile ? "text-ink" : "text-muted",
                )}
              >
                {selectedFile?.name ?? importCopy.noFileSelected}
              </p>
              <p className="text-caption uppercase tracking-caption text-muted">
                {importCopy.excelFormat}
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

      <PageActions placement="form">
        <Button
          type="button"
          size="lg"
          pending={isPending}
          aria-label={isPending ? pendingAriaLabel : undefined}
          className="self-start"
          disabled={!selectedFile || fileDisabled || uploadDisabled}
          onClick={onUpload}
        >
          {isPending ? (
            <Spinner data-icon="inline-start" aria-hidden="true" />
          ) : (
            <FileUp data-icon="inline-start" />
          )}
          {isPending ? pendingLabel : uploadLabel}
        </Button>
      </PageActions>

      {children}
    </PageSection>
  );
}
