import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { downloadImportFailureReport, importCandidates } from "@/api/imports";
import { ImportPanel } from "@/components/admin/ImportPanel";
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { adminPageCopy, adminPageText, importCopy } from "@/lib/pageCopy";
import type { ImportFailure } from "@/types/imports";

export function CandidateImportPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (selected: File) => importCandidates(examId, selected),
    onSuccess: () => {
      setNotice({ tone: "success", message: importCopy.rosterImportComplete });
      queryClient.invalidateQueries({ queryKey: ["admin", "absent-candidates"] });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, importCopy.rosterImportFailed) }),
  });

  const handleDownloadFailureReport = async (batchId: number) => {
    try {
      await downloadImportFailureReport(batchId);
      setNotice({ tone: "success", message: importCopy.failureReportStarted });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, importCopy.failureReportFailed) });
    }
  };

  return (
    <PageShell data-testid="candidate-import-shell" density="workbench" width="default" stagger>
      <PageHeader
        eyebrow={adminPageCopy.roster}
        title={adminPageText.roster.importTitle}
        description={adminPageText.roster.importDescription}
      />

      <ImportPanel
        fileInputId="candidate-file"
        fileLabel={importCopy.selectExcelFile}
        selectedFile={file}
        onFileChange={setFile}
        uploadLabel={importCopy.uploadRoster}
        pendingLabel={importCopy.importing}
        pendingAriaLabel="正在导入应考名单"
        isPending={mutation.isPending}
        onUpload={() => file && mutation.mutate(file)}
      />

      {notice ? (
        <Alert variant={notice.tone === "success" ? "success" : "error"}>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

      {mutation.data ? (
        <PageSection variant="card" className="gap-3 p-6">
          <p className="text-body text-ink">
            成功 <span className="font-mono">{mutation.data.success_count}</span> 行，失败{" "}
            <span className="font-mono text-error">{mutation.data.failed_count}</span> 行
          </p>
          {mutation.data.failed_count > 0 ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="self-start"
              onClick={() => void handleDownloadFailureReport(mutation.data.batch_id)}
            >
              <Download data-icon="inline-start" />
              下载失败明细
            </Button>
          ) : null}
          {mutation.data.failures.length ? (
            <>
              <Separator />
              <ul className="flex flex-col gap-1 text-caption text-muted">
                {mutation.data.failures.map((failure: ImportFailure) => (
                  <li key={failure.row_number} className="font-mono">
                    行 {failure.row_number} · {failure.reason}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </PageSection>
      ) : null}
    </PageShell>
  );
}
