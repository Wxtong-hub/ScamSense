# 拆招 · ScamSense

一个给第一次找实习、找工作的学生用的求职反诈训练室：向三位虚构联系人分别提问，核对消息来源，作出决定，再回看自己说过的哪些话构成了证据。

**v0.1.0 是可运行的本地规则演示，不需要模型密钥，不会向外部 AI 发送对话。** 它不是招聘平台，也不会鉴定真实招聘方。正式 E01–E16 剧本和大模型适配尚未接入；本仓库不是已经上线的比赛体验链接。

## 运行（两个终端）

需要 Python 3.13、Node.js 22.12+ 和 npm。从仓库根目录开始。

**终端一 · API（Windows PowerShell）**

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS/Linux 用 `python3.13 -m venv .venv`，后续 Python 命令使用 `.venv/bin/python`。只运行服务也可安装 `requirements.txt`。健康检查：`http://127.0.0.1:8000/healthz`。

**终端二 · 前端**

```sh
cd frontend
npm ci --ignore-scripts
npm run dev
```

打开 **http://127.0.0.1:5173/**。本地 Vite 把 `/api` 转给 8000 端口，不需要域名、云服务器或 `.env`。后端默认把 SQLite 放在 `backend/data/`，此目录不提交到 Git。

## 五步体验

1. 进入训练。浏览器当前标签页获得匿名会话，刷新可继续。
2. 选林悦、陈浩或王宇，问一句关于岗位或授权关系的问题。点击推荐问题只是填入输入框，仍由你决定是否发送。
3. 切到另一位联系人核对，明确说出线索，例如“群里只是转述，不能证明招聘主体已经授权”。不要输入真实资料。
4. 点击「提交决定」，选择继续、拒绝、暂缓或进一步核实，可附上理由；也可以提前结束。
5. 打开复盘，从分项下面的引文跳回当时的私聊；没有观察机会时显示“证据不足”，不捏造总分。

## 实现与边界

- Vue 3、TypeScript、Vite、Pinia、Vue Router（hash 路由）、Element Plus 对话框。静态构建输出在 `frontend/dist/`。
- FastAPI、Pydantic、SQLAlchemy 2、SQLite、Alembic。Bearer 凭证只授权一场训练；服务端仅存摘要。每个角色只读自身历史。本地规则先算出完整回复，再通过 SSE 分段发送；断线后刷新能找回已提交的消息，不会触发第二次生成。
- 判断循证而非猜人：风险识别 25%、主动核实 30%、决策合理性 25%、证据分析 20%。展示回执、主动识别和核实行为分别记录；同一核实方向重复不叠加。首版采用受限的中文关键词规则，不能覆盖所有同义表达，不用于能力鉴定。
- 演示量限制：每场最多 48 次提问，每条消息和决策理由最多 500 字，同一后端每小时最多创建 120 场。会话 7 天到期，到期后不能访问，下次创建会话时清理旧记录；不承诺关机时也物理删除数据。只用虚构资料；简单的输入筛查不能保证识别所有个人信息。
- 环境示例：`frontend/.env.example`、`backend/.env.example`。后端读取**进程环境变量**；`DATABASE_URL` 应指向持久目录，`CORS_ALLOWED_ORIGINS` 是用逗号分隔的精确前端 Origin。生产静态构建需先配置 `VITE_API_BASE_URL` 为后端 HTTPS 基址（含 `/api/v1`）；不要把任何凭据放进 `VITE_*`。
- [架构设计与官方赛事要求](docs/architecture.md) 描述目标架构，不能当作 v0.1 已实现清单。正式参赛前需补充剧情、确认外接 API 的赛事口径并独立完成 Sites 公网部署及服务器验收。

## 验证

在 `backend/` 中用虚拟环境 Python 执行 `python -m pytest -q`。测试对临时 SQLite 执行真实迁移，不使用开发会话，也不需要网络或模型额度。在 `frontend/` 中运行 `npm run build` 做类型检查并构建静态资源。

2026-11-19 核验：`npm audit --omit=dev` 未报告运行依赖漏洞；全量审计仍报告 6 条高危开发工具链告警（包括 Vite、vue-tsc 的传递依赖）。仅在本机可信源码上使用开发服务器和构建工具，不把 Vite 开发服务暴露公网；正式发布前复查锁文件和上游修复。
