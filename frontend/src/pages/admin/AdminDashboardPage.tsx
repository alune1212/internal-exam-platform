import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const metrics = [
  { label: "题库题目", value: "0" },
  { label: "已发布考试", value: "0" },
  { label: "已提交记录", value: "0" },
  { label: "未参加人员", value: "0" },
];

export function AdminDashboardPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">管理仪表盘</h2>
        <p className="text-muted-foreground">第一阶段展示核心入口，后续接入实时统计。</p>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">{metric.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{metric.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
