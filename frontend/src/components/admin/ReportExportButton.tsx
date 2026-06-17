import { useMutation } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { getErrorMessage } from "@/api/client";
import { downloadReportExport } from "@/api/reports";
import { Button } from "@/components/ui/button";

export function ReportExportButton({ examId }: { examId?: string | null }) {
  const mutation = useMutation({ mutationFn: () => downloadReportExport(examId) });

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        <Download data-icon="inline-start" />
        {mutation.isPending ? "导出中" : examId ? "导出当前考试" : "导出全部报表"}
      </Button>
      {mutation.isSuccess ? (
        <span className="text-caption text-success" role="alert">
          报表已开始下载。
        </span>
      ) : null}
      {mutation.isError ? (
        <span className="text-caption text-error" role="alert">
          {getErrorMessage(mutation.error, "报表导出失败")}
        </span>
      ) : null}
    </div>
  );
}
