import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { downloadImportFailureReport, importCandidates } from "@/api/imports";
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { adminPageCopy } from "@/lib/pageCopy";
import type { ImportFailure } from "@/types/imports";

export function CandidateImportPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (selected: File) => importCandidates(examId, selected),
    onSuccess: () => {
      setNotice({ tone: "success", message: "应考人员导入完成。" });
      queryClient.invalidateQueries({ queryKey: ["absent-candidates"] });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "应考人员导入失败") }),
  });

  const handleDownloadFailureReport = async (batchId: number) => {
    try {
      await downloadImportFailureReport(batchId);
      setNotice({ tone: "success", message: "失败明细已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "失败明细下载失败") });
    }
  };

  return (
    <PageShell data-testid="candidate-import-shell" density="workbench" width="default" stagger>
      <PageHeader
        eyebrow={adminPageCopy.candidates}
        title="应考人员导入"
        description="上传人员 Excel 模板，系统会按当前考试写入应考名单。"
      />

      <PageSection variant="panel" className="lg:p-8">
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="candidate-file">选择 Excel 文件</FieldLabel>
            <Input
              id="candidate-file"
              type="file"
              accept=".xlsx,.xls"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </Field>
        </FieldGroup>
        <Button
          type="button"
          size="lg"
          className="self-start"
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate(file)}
        >
          {mutation.isPending ? (
            <Spinner data-icon="inline-start" aria-label="正在导入应考人员" />
          ) : (
            <FileUp data-icon="inline-start" />
          )}
          {mutation.isPending ? "正在导入..." : "上传应考人员"}
        </Button>
      </PageSection>

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
