# 晴旅：天气旅行助手

晴旅是一款中文天气与旅行建议助手：先查询和风天气真实数据，再由大模型结合用户问题生成易读、可执行的回答。未配置大模型时，系统仍可使用内置规则完成基础天气查询。

## 功能

- 查询城市当前、今日及未来 3～7 天预报，理解“明天”“后天”“最近几天”等说法。
- 询问温度、湿度、风速、降雨概率等指标。
- 询问景点出行建议，例如“后天去颐和园适合吗”。景点先经和风地理服务定位，常见景点映射仅作兜底。
- 网页和命令行持续对话，支持新建、切换、查看、删除会话。
- SQLite 保存会话消息和天气快照；天气缓存默认 120 秒。

## 工作流程

```text
用户问题 -> 意图识别 -> 地点解析 -> 和风天气查询/缓存
         -> 大模型生成建议（失败时回退为标准化回答）
         -> 保存会话并返回结构化天气卡片
```

普通城市天气不会进行 POI 地理编码，避免有效城市因景点查询失败而中断。

## 技术栈

Python 3.11+、FastAPI、Uvicorn、Pydantic、SQLite、和风天气 API、OpenAI 兼容模型 API、原生 HTML/CSS/JavaScript、pytest、respx。

## 快速开始

### 安装

```powershell
uv sync --extra test
```

### 配置

```powershell
Copy-Item .env.example .env
```

至少填写：

```text
QWEATHER_API_KEY=你的和风天气Key
QWEATHER_API_HOST=https://devapi.qweather.com
```

启用大模型时填写 `LLM_API_KEY`、`LLM_MODEL`，兼容服务再填写 `LLM_BASE_URL`。`.env` 已被 Git 忽略，禁止提交真实 Key。

和风天气 Key 必须授权对应 Host；商业版按控制台分配的专属 Host 配置。若出现 `invalid-host`，请检查 Key 与 Host 的授权关系。只有天气和地理服务使用不同域名时才设置 `QWEATHER_GEO_HOST`。

### 启动网页

```powershell
uv run weather-api
```

打开 <http://127.0.0.1:8000/>；`/docs` 是 Swagger 文档，`/health` 是无需 Key 的健康检查，`/web/` 提供静态资源。VS Code 中复制 `.env.example` 为 `.env` 后按 `F5`，选择“启动天气助手”即可。

### 启动 CLI

```powershell
uv run weather-agent
```

输入问题后回车；输入 `退出`、`quit` 或 `exit` 结束。

## 配置参考

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `QWEATHER_API_KEY` | — | 和风天气 Key（必填） |
| `QWEATHER_API_HOST` | `https://devapi.qweather.com` | 天气 Host |
| `QWEATHER_GEO_HOST` | 天气 Host | 不同地理 Host 时覆盖 |
| `LLM_API_KEY` / `LLM_MODEL` | — | 同时配置以启用模型 |
| `LLM_BASE_URL` | SDK 默认地址 | OpenAI 兼容接口地址 |
| `WEATHER_DB_PATH` | `src/weather_agent/weather_agent.db` | SQLite 路径 |
| `WEATHER_CACHE_TTL_SECONDS` | `120` | 缓存秒数 |
| `WEATHER_TIMEOUT_SECONDS` | `8` | 请求超时秒数 |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | 服务监听地址和端口 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## API

### `POST /api/chat`

```json
{"message":"后天去颐和园旅游适合吗？","conversation_id":1}
```

首次发送可省略 `conversation_id`，服务自动创建会话；不存在的 ID 返回 `404`。响应包含 `reply`、`status` 和可选结构化 `weather`：

```json
{"reply":"…","status":"success","weather":{"location":"北京","date":"2026-09-09","source":"QWeather"}}
```

`status` 为 `success`、`clarification`（需补充地点）、`unsupported` 或 `error`。天气服务失败时不会伪造温度等数值。

### 会话接口

- `GET /api/conversations`：会话列表（按更新时间倒序）
- `POST /api/conversations`：新建会话
- `GET /api/conversations/{id}`：会话详情、消息和天气快照
- `DELETE /api/conversations/{id}`：删除会话及其消息

## 示例问题

`上海今天会下雨吗？` · `北京当前温度和风速是多少？` · `哈尔滨最近几天天气怎么样？` · `后天去颐和园旅游适合吗？` · `明天去故宫需要带伞吗？` · `周末去西湖，上午还是下午更合适？`

## 测试与验收

测试使用 mock，不依赖真实天气网络或模型额度：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

当前共 58 项测试，覆盖意图解析、日期识别、缓存、地点解析、错误回退、SQLite 会话、FastAPI、网页资源和 CLI 退出流程。交付前应确认测试通过，并访问 `/health` 做启动冒烟检查。

## 项目结构

```text
src/weather_agent/
├── agent.py                 # 意图协调、天气查询、回答和回退
├── api.py                   # FastAPI 路由和静态页面入口
├── cache.py                 # TTL 天气缓存
├── cli.py                   # 命令行模式
├── config.py                # .env 加载
├── database.py              # SQLite 会话存储
├── factory.py               # Agent 组装
├── llm.py                   # OpenAI 兼容模型适配
├── location.py              # 地点解析和兜底映射
├── providers/qweather.py    # 和风天气适配器
└── web/                     # 前端页面、样式和脚本
tests/                       # 单元、API 和网页测试
docs/                        # 技术方案与产品设计
```

## 常见问题

**缺少 Key**：确认 `.env` 在项目根目录且变量名正确，重启进程。

**`invalid-host`**：改用控制台为该 Key 分配的 `QWEATHER_API_HOST`，必要时单独设置 `QWEATHER_GEO_HOST`。

**模型不可用**：模型抽取或生成失败会回退为规则回答；未配置模型时基础天气查询仍可用。

**页面未更新**：执行 Ctrl+F5 硬刷新并确认端口正确。

## 当前边界

当前版本为单用户模式，不包含登录、权限和按用户隔离。预报仅覆盖和风天气可可靠提供的未来范围，系统不会猜测超出范围的天气。多用户部署时应增加用户表、认证和会话隔离。
