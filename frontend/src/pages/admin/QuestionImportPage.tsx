import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";

import { getErrorMessage } from "@/api/client";
import {
  downloadImportFailureReport,
  downloadImportTemplate,
  importQuestions,
} from "@/api/imports";
import { ImportPanel } from "@/components/admin/ImportPanel";
import { PageActions, PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { adminPageCopy, adminPageText, importCopy } from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";
import type { ImportFailure } from "@/types/imports";

export function QuestionImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: importQuestions,
    onSuccess: () => {
      setNotice({ tone: "success", message: importCopy.questionImportComplete });
      void queryClient.invalidateQueries({ queryKey: adminKeys.questions() });
    },
    onError: (error) =>
      setNotice({
        tone: "error",
        message: getErrorMessage(error, importCopy.questionImportFailed),
      }),
  });

  const handleDownloadTemplate = async () => {
    try {
      await downloadImportTemplate("questions");
      setNotice({ tone: "success", message: "题库导入模板已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "题库导入模板下载失败") });
    }
  };

  const handleDownloadFailureReport = async (batchId: number) => {
    try {
      await downloadImportFailureReport(batchId);
      setNotice({ tone: "success", message: importCopy.failureReportStarted });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, importCopy.failureReportFailed) });
    }
  };

  return (
    <PageShell data-testid="question-import-shell" density="workbench" width="standard">
      <PageHeader
        eyebrow={adminPageCopy.questionImport}
        title={adminPageText.questionImport.title}
        description={adminPageText.questionImport.description}
      />

      <ImportPanel
        fileInputId="question-file"
        fileLabel={importCopy.selectExcelFile}
        selectedFile={file}
        onFileChange={setFile}
        uploadLabel={importCopy.uploadQuestionBank}
        pendingLabel={importCopy.importing}
        pendingAriaLabel="正在导入题库"
        isPending={mutation.isPending}
        onUpload={() => file && mutation.mutate(file)}
        templateAction={
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleDownloadTemplate()}
          >
            <Download data-icon="inline-start" />
            {importCopy.questionTemplate}
          </Button>
        }
      />

      {notice ? (
        <Alert variant={notice.tone === "success" ? "success" : "error"}>
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

      {mutation.data ? (
        <PageSection variant="summary" data-testid="question-import-result">
          <p className="text-body text-ink">
            成功 <span className="font-mono">{mutation.data.success_count}</span> 行，失败{" "}
            <span className="font-mono text-error">{mutation.data.failed_count}</span> 行
          </p>
          {mutation.data.failed_count > 0 ? (
            <PageActions placement="card" aria-label="导入结果操作">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void handleDownloadFailureReport(mutation.data.batch_id)}
              >
                <Download data-icon="inline-start" />
                下载失败明细
              </Button>
            </PageActions>
          ) : null}
          {mutation.data.failures.length ? (
            <>
              <Separator />
              <ul className="flex min-w-0 flex-col gap-2 text-body-sm text-muted">
                {mutation.data.failures.map((failure: ImportFailure) => (
                  <li key={failure.row_number} className="flex min-w-0 gap-2 break-words">
                    <span className="shrink-0 font-mono text-caption">行 {failure.row_number}</span>
                    <span className="min-w-0 break-words">{failure.reason}</span>
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
