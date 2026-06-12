import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { useParams } from "react-router-dom";

import { importCandidates } from "@/api/imports";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function CandidateImportPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const mutation = useMutation({
    mutationFn: (selectedFile: File) => importCandidates(examId, selectedFile),
  });

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>应参人员导入</CardTitle>
        <CardDescription>未参加人员名单基于应参人员减去已提交考试人员计算。</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Input
          type="file"
          accept=".xlsx,.xls"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <Button
          type="button"
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate(file)}
        >
          <FileUp data-icon="inline-start" />
          上传应参人员
        </Button>
        {mutation.data ? (
          <div className="rounded-md border p-4 text-sm">
            成功 {mutation.data.success_count} 行，失败 {mutation.data.failed_count} 行
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
