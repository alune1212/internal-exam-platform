import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileUp } from "lucide-react";
import { useState } from "react";

import { getErrorMessage } from "@/api/client";
import {
  downloadImportFailureReport,
  downloadImportTemplate,
  importQuestions,
} from "@/api/imports";
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { adminPageCopy } from "@/lib/pageCopy";
import type { ImportFailure } from "@/types/imports";

export function QuestionImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: importQuestions,
    onSuccess: () => {
      setNotice({ tone: "success", message: "题库导入完成。" });
      queryClient.invalidateQueries({ queryKey: ["admin-questions"] });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "题库导入失败") }),
  });

  const handleDownloadTemplate = async () => {
    try {
      await downloadImportTemplate("questions");
      setNotice({ tone: "success", message: "模板已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "模板下载失败") });
    }
  };

  const handleDownloadFailureReport = async (batchId: number) => {
    try {
      await downloadImportFailureReport(batchId);
      setNotice({ tone: "success", message: "失败明细已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "失败明细下载失败") });
    }
  };

  return (
    <PageShell data-testid="question-import-shell" density="workbench" width="default" stagger>
      <PageHeader
        eyebrow={adminPageCopy.library}
        title="题库导入"
        description="仅支持标准 Excel（.xlsx / .xls），不解析 Word。系统会校验行数据并保存可用题目。"
      />

      <PageSection variant="panel" className="rounded-lg p-6 lg:p-8">
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleDownloadTemplate()}
          >
            <Download data-icon="inline-start" />
            下载模板
          </Button>
        </div>

        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="question-file">选择 Excel 文件</FieldLabel>
            <Input
              id="question-file"
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
            <Spinner data-icon="inline-start" aria-label="正在导入题库" />
          ) : (
            <FileUp data-icon="inline-start" />
          )}
          {mutation.isPending ? "正在导入..." : "上传并校验"}
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
