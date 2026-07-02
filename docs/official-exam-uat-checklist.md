# Official Exam UAT Checklist

正式考试前用 Docker/Nginx 入口 `http://localhost:8080` 跑一遍。目标是验证主链，不扩展成完整 LMS 验收。

## Preflight

```bash
cp .env.example .env  # 首次执行；正式环境必须替换里面的口令和密钥
cd backend
uv run ruff format . --check
uv run ruff check .
uv run ty check
uv run pytest
cd ../frontend
npm run format:check
npm test -- --run
npm run lint
npm run build
cd ..
docker compose --env-file .env config
docker compose up -d --build
docker compose exec -T backend uv run alembic upgrade head
docker compose exec -T nginx nginx -t
curl -f http://localhost:8080/api/health
curl -f http://localhost:8080/docs
```

Compose 使用 `.env` 里的 `db` 主机名连接数据库，后端 `8000` 只暴露给容器网络。`curl http://localhost:8000/api/health` 仅适用于直接用 `uvicorn` 启动后端并配置本机可达数据库的开发场景；Docker/Nginx UAT 统一走 `http://localhost:8080`。

生产环境必须先确认：

- `POSTGRES_PASSWORD` 不是示例值。
- `DATABASE_URL` 使用正式数据库凭据。
- `ADMIN_PASSWORD` 不是默认值。
- `TOKEN_SECRET` 不是默认值。
- `ENVIRONMENT=production` 时，后端会拒绝默认 `ADMIN_PASSWORD`、默认 `TOKEN_SECRET`、空 CORS、`*`、非 HTTPS，以及 localhost/127.0.0.1/0.0.0.0；正式环境的 `CORS_ORIGINS` 只包含正式 HTTPS 前端/Nginx 域名。
- 如需调整导入预算，显式配置 `IMPORT_MAX_UPLOAD_BYTES`、`IMPORT_MAX_ROWS`、`IMPORT_MAX_SHEETS`；默认是 5 MiB、5000 行、1 个工作表。
- 已做数据库备份，再执行 `alembic upgrade head`。

## Browser Flow

1. 打开 `http://localhost:8080/exams`，在没有考试人 session 时确认返回登录页，且不会渲染考试列表。
2. 打开 `http://localhost:8080/admin/login`，管理员登录成功。
3. 导入一份包含失败行的题库 Excel，确认结果页显示失败行，并能下载失败报告。
4. 导入一份包含失败行的应考名单 Excel，确认结果页显示失败行，并能下载失败报告。
5. 新建或编辑考试，配置 `available_from` / `available_until`、时长、固定试卷规则。
6. 进入单场考试名单页，导入名单，确认成功/失败统计和失败报告下载。
7. 发布考试为 active，确认列表显示发布状态、开放窗口、冻结题池数量。
8. 用名单内考试人登录，打开考试列表。
9. 在开放窗口前确认显示未开始且不可新开考。
10. 到开放窗口内进入考试，确认题目来自 frozen pool，题数/总分符合规则。
11. 暂存答案，刷新页面，确认已有 attempt 可继续。
12. 交卷，确认结果页显示分数、是否通过；若考试关闭答案回看，确认不显示答案解析。
13. 在管理端名单页为该考试人授权补考，确认考试人端重新出现该考试并能生成新的补考 attempt。
14. 在开放窗口结束后刷新已有进行中 attempt，确认仍可继续，倒计时仍按 `started_at + duration_minutes`。
15. 回到管理端报表，选择该考试，确认成绩、题目正确率、错题排行、参考状态不混入其他考试，并以该考试的当前参考 attempt 为准。
16. 导出当前考试报表，确认 Excel 包含个人成绩、题目正确率、错题排行、参考状态四个 sheet。

## Stop Conditions

- 失败报告无法下载或缺少批次元信息。
- 发布后题库修改影响已发布考试抽题。
- 考试窗口结束后可以新开考。
- 已开始 attempt 因 `available_until` 结束无法恢复。
- 补考授权后考试人无法重新进入考试，或补考未生成新的 attempt。
- 报表默认混入其他考试数据。
- 无考试人 session 访问 `/exams` 时渲染考试列表，或触发 `/api/exams/active` 匿名请求。
- Docker/Nginx `8080` 健康检查失败。
