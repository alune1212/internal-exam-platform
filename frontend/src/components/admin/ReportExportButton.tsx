import { useMutation } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { getErrorMessage } from "@/api/client";
import { downloadReportExport } from "@/api/reports";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function ReportExportButton({ examId }: { examId?: string | null }) {
  const mutation = useMutation({ mutationFn: () => downloadReportExport(examId) });

  return (
    <div data-report-export="" className="flex min-w-0 flex-col items-stretch gap-2 sm:items-start">
      <Button
        type="button"
        size="sm"
        variant="outline"
        pending={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        <Download data-icon="inline-start" />
        {mutation.isPending ? "导出中" : examId ? "导出当前考试" : "导出全部报表"}
      </Button>
      {mutation.isSuccess ? (
        <Alert variant="success" className="py-2">
          <AlertDescription>报表已开始下载。</AlertDescription>
        </Alert>
      ) : null}
      {mutation.isError ? (
        <Alert variant="error" className="py-2">
          <AlertDescription>{getErrorMessage(mutation.error, "报表导出失败")}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
