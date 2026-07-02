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
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { adminPageCopy, importCopy } from "@/lib/pageCopy";
import type { ImportFailure } from "@/types/imports";

export function QuestionImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: importQuestions,
    onSuccess: () => {
      setNotice({ tone: "success", message: importCopy.questionImportComplete });
      queryClient.invalidateQueries({ queryKey: ["admin", "questions"] });
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
    <PageShell data-testid="question-import-shell" density="workbench" width="default" stagger>
      <PageHeader
        eyebrow={adminPageCopy.questionImport}
        title="题库导入"
        description="仅支持标准 Excel（.xlsx / .xls），不解析 Word。系统会校验行数据并保存可用题目。"
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
