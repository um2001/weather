# 晴旅：天气旅行助手

一个基于 FastAPI、原生 JavaScript 和大模型的中文天气旅行助手。用户可以查询城市天气，也可以询问“后天去颐和园适合吗”这类问题。程序先从和风天气获取真实天气，再让大模型基于天气数据生成出行建议。

## 功能

- 查询当前、今日和未来几天天气
- 识别明天、后天等自然语言日期
- 大模型识别任意景点名称，和风地理服务验证景点并获取坐标
- 常见景点映射仅作为地点服务不可用时的兜底
- 根据温度、降雨概率和天气状况生成旅游建议
- SQLite 保存单用户会话历史和天气快照
- 新建、切换、查看和删除会话
- 响应式网页界面，支持桌面和移动端

## 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- Pydantic
- SQLite
- 和风天气 API
- OpenAI 兼容大模型 API
- 原生 HTML、CSS、JavaScript
- pytest、respx

## 配置

在启动前设置环境变量：

```text
QWEATHER_API_KEY=你的和风天气Key
QWEATHER_API_HOST=https://你的专属域名.re.qweatherapi.com
# 可选：只有天气和地理服务分配了不同域名时才需要填写
# QWEATHER_GEO_HOST=https://geoapi.qweather.com
LLM_API_KEY=你的模型Key
LLM_MODEL=模型名称
LLM_BASE_URL=https://你的兼容接口/v1
WEATHER_DB_PATH=src/weather_agent/weather_agent.db
```

`LLM_BASE_URL` 可选；不设置时使用模型 SDK 默认地址。未设置 `WEATHER_DB_PATH` 时，数据库默认保存在 `src/weather_agent/weather_agent.db`。API Key 只在后端使用，不会返回给浏览器。

### VS Code 一键启动

首次使用时，将 `.env.example` 复制为 `.env`，填写自己的 Key 与模型名称。`.env` 已被 Git 忽略；之后在 VS Code 中按 `F5` 并选择“启动天气助手”，即可自动加载配置并启动服务，无需每次在终端设置环境变量。

和风天气的 Key 必须授权对应的 API Host：免费开发版通常使用 `devapi.qweather.com`，商业版按控制台分配的专属 Host 配置。若只有一个专属 Host，设置 `QWEATHER_API_HOST` 即可，地理查询会自动复用它；只有天气和地理服务分配了不同域名时才设置 `QWEATHER_GEO_HOST`。若日志出现 `invalid-host`，请在和风控制台确认 Key 已授权该 Host。

## 安装和运行

```powershell
uv sync
uv run weather-api
```

打开 <http://127.0.0.1:8000/> 使用网页，API 文档位于 `/docs`，健康检查位于 `/health`。

## 示例问题

- `上海今天会下雨吗？`
- `后天去颐和园旅游适合吗？`
- `明天去故宫需要带伞吗？`
- `周末去西湖，上午还是下午更合适？`

## API

- `POST /api/chat`：发送消息，可带 `conversation_id`
- `GET /api/conversations`：会话列表
- `POST /api/conversations`：新建会话
- `GET /api/conversations/{id}`：会话详情和消息
- `DELETE /api/conversations/{id}`：删除会话

聊天响应包含 `reply`、`status` 和可选的结构化 `weather` 字段，前端使用该字段渲染天气卡片。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

测试使用 mock，不依赖真实天气网络。生产使用时请关注和风天气 API 的额度、Key 权限和预报范围；超出可可靠预报范围的日期不会由模型自行猜测。

## 项目结构

```text
src/weather_agent/
├── agent.py                 # 意图协调、天气查询和回答生成
├── api.py                   # FastAPI 和会话接口
├── database.py              # SQLite 会话存储
├── llm.py                   # OpenAI 兼容模型适配
├── location.py              # 城市别名和地点兜底映射
├── providers/qweather.py    # 和风天气适配器
└── web/                     # 原生前端页面
tests/                       # 单元测试和 API 测试
```

当前版本是单用户模式，不包含登录和权限系统。若部署给多个用户，下一步应增加用户表、认证和按用户隔离会话。
