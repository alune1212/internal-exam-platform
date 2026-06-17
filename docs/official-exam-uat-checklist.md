# Official Exam UAT Checklist

正式考试前用 Docker/Nginx 入口 `http://localhost:8080` 跑一遍。目标是验证主链，不扩展成完整 LMS 验收。

## Preflight

```bash
cd backend && uv run alembic upgrade head
cd backend && uv run pytest
cd frontend && npm test -- --run
cd frontend && npm run lint
cd frontend && npm run build
docker compose config
docker compose up -d --build
curl http://localhost:8000/api/health
curl http://localhost:8080/api/health
```

生产环境必须先确认：

- `ADMIN_PASSWORD` 不是默认值。
- `TOKEN_SECRET` 不是默认值。
- `CORS_ORIGINS` 只包含正式前端/Nginx 域名。
- 已做数据库备份，再执行 `alembic upgrade head`。

## Browser Flow

1. 打开 `http://localhost:8080/admin/login`，管理员登录成功。
2. 导入一份包含失败行的题库 Excel，确认结果页显示失败行，并能下载失败报告。
3. 导入一份包含失败行的人员 Excel，确认结果页显示失败行，并能下载失败报告。
4. 新建或编辑考试，配置 `available_from` / `available_until`、时长、固定试卷规则。
5. 进入单场考试名单页，导入名单，确认成功/失败统计和失败报告下载。
6. 发布考试为 active，确认列表显示发布状态、开放窗口、冻结题池数量。
7. 用名单内考生登录，打开考试列表。
8. 在开放窗口前确认显示未开始且不可新开考。
9. 到开放窗口内进入考试，确认题目来自 frozen pool，题数/总分符合规则。
10. 暂存答案，刷新页面，确认已有 attempt 可继续。
11. 提交试卷，确认结果页显示分数、是否通过；若考试关闭答案回看，确认不显示答案解析。
12. 在开放窗口结束后刷新已有进行中 attempt，确认仍可继续，倒计时仍按 `started_at + duration_minutes`。
13. 回到管理端报表，选择该考试，确认成绩、题目正确率、错题排行、参考状态不混入其他考试。
14. 导出当前考试报表，确认 Excel 包含成绩报表、题目正确率、错题统计、参考状态四个 sheet。

## Stop Conditions

- 失败报告无法下载或缺少批次元信息。
- 发布后题库修改影响已发布考试抽题。
- 考试窗口结束后可以新开考。
- 已开始 attempt 因 `available_until` 结束无法恢复。
- 报表默认混入其他考试数据。
- Docker/Nginx `8080` 健康检查失败。
