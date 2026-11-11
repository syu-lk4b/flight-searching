# Multi-Agent Flight Search Skill (`multi-agent-flight-search`)
# 多 Agent 特价机票并行搜索技能

[English](#english) | [中文说明](#中文说明)

---

<a name="english"></a>
## ✈️ English Guide

### 1. Overview
`multi-agent-flight-search` is a reusable AI Agent Skill and zero-dependency Python CLI toolkit that coordinates **multiple parallel sub-agents** to search across major airlines (Full-Service Carriers & Low-Cost Carriers) and OTA platforms for the **cheapest tax-inclusive flight combinations** across a multi-month date window, specific departure weekdays, fixed trip durations, and multiple destination cities.

It aggregates and cross-verifies three complementary, captcha-free real-time data sources:
1. **Trip.com International Calendar API (`hk.trip.com`)** — Rapidly scans round-trip nonstop lowest tax-inclusive fares (`CNY`) across an entire 90-day window, capturing hidden full-service carrier promos (e.g., Juneyao Air / China Eastern with `2×23kg` free checked baggage).
2. **Spring Airlines Direct Real-Time Endpoint (`hk.ch.com`)** — Queries live `9C` / `IJ` nonstop flights, exact tax breakdowns, and hand/checked baggage allowances (bypassing the `null` false-sold-out bug on trend endpoints).
3. **Google Flights (`ds:1` Embedded Data)** — Extracts nonstop flight numbers, departure/arrival times, aircraft types, and round-trip tax-inclusive fares across global full-service and low-cost airlines.

---

### 2. Repository Structure
```text
.
├── LICENSE
├── README.md
├── skills/
│   └── multi-agent-flight-search/
│       ├── SKILL.md                        # Agent skill definition (workflow, triggers, pitfalls, verification)
│       └── scripts/
│           └── flight_query_helper.py      # Zero-dependency Python 3 query CLI
└── examples/
    ├── shanghai_japan_top5_flights_report.md   # Sample report: Shanghai <-> Japan (Mon-Fri, 5D4N)
    └── shanghai_korea_top5_flights_report.md   # Sample report: Shanghai <-> South Korea (Mon-Fri, 5D4N)
```

---

### 3. How to Use

#### Option A: Use as an AI Agent Skill (Pi / Claude / Agent Harness)
1. **Install the skill** into your agent's skill directory:
   ```bash
   # For Pi coding agent (global skill):
   mkdir -p ~/.pi/agent/pi-hermes-memory/skills/
   cp -r skills/multi-agent-flight-search ~/.pi/agent/pi-hermes-memory/skills/

   # Or for standard ~/.agents/skills/ loader:
   mkdir -p ~/.agents/skills/
   cp -r skills/multi-agent-flight-search ~/.agents/skills/
   ```
2. **Trigger via natural language prompts**:
   Once installed, simply ask your agent in natural language:
   - *"Search for the Top 5 cheapest nonstop round-trip flights from Shanghai to any city in Japan over the next 3 months, departing on Monday for a 5-day trip."*
   - *"Use multi-agent flight search to find the cheapest flights from Shanghai to South Korea next month."*
   - *"Compare cheap flights to Tokyo and Osaka in December, departing Thursday for 4 days."*

3. **What the Agent Does Automatically**:
   - **Step 1 (Date-Route Matrix)**: Generates all valid `(departure_date, return_date)` pairs matching your weekday and duration constraints.
   - **Step 2 (Parallel Regional Sub-Agents)**: Spawns 3–4 parallel sub-agents partitioned by destination region (e.g., Kanto, Kansai/Chubu, Kyushu/Hokkaido) to query all date pairs concurrently.
   - **Step 3 (Cross-Verification & Baggage Audit)**: Merges regional JSON results, cross-checks exact return flight numbers, terminals, and baggage policies (clearly distinguishing LCC `7kg` hand-carry-only fares from FSC `1–2×23kg` checked-baggage fares).
   - **Step 4 (Dual-View Report)**: Outputs both a **De-duplicated Top 5 Best Combinations by Route/Airline** and a **Strict Absolute Cheapest Top 10 Table**, plus a full-period price matrix.

#### Option B: Standalone CLI Usage (`flight_query_helper.py`)
Requires **Python 3.8+** (uses standard library only; no `pip install` needed).

```bash
# View help
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py --help

# 1. Trip.com low-price calendar (e.g., SHA -> NGO, 90 days from 2026-11-11, Monday=0, 5-day trip)
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py \
  trip_calendar SHA NGO 2026-11-11 90 0 5

# 2. Spring Airlines (9C / IJ) real-time single-day nonstop query (e.g., PVG -> CJU)
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py \
  ch_day PVG CJU 2026-11-16

# 3. Google Flights nonstop round-trip query (e.g., PVG -> ICN, 2026-11-30 to 2026-12-04)
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py \
  gflights PVG ICN 2026-11-30 2026-12-04
```

---

### 4. Security & Privacy
- **Zero Secrets / Credentials**: This project uses **only public, unauthenticated read-only flight search endpoints** over `HTTPS`. No API keys, OAuth tokens, cookies, session IDs, or personal user data are used or stored.
- **Strict Input Validation**: All IATA airport/city codes (`^[A-Za-z]{3}$`) and dates (`YYYY-MM-DD`) are validated and URL-encoded prior to network calls to prevent parameter or header injection.
- **Zero Third-Party Dependencies**: `flight_query_helper.py` relies solely on the Python 3 standard library (`urllib`, `json`, `re`, `datetime`), eliminating supply-chain risks from external packages.

---

<a name="中文说明"></a>
## ✈️ 中文使用指南 (How to Use)

### 1. 项目简介
`multi-agent-flight-search` 是一个可复用的 **AI Agent 机票比价技能（Skill）与零依赖 Python 查询工具集**。它通过编排**多个并行子 Agent（Sub-Agents）**，同时扫描各大全服务航空公司、廉价航空公司与国际比价平台，在指定的时间跨度（如未来 3 个月）、特定出发星期（如周一出发）和固定行程天数（如 5 天 4 晚）下，自动找出**跨目的地最便宜的含税往返机票组合**。

本技能内置三大免验证码实时数据源，并实现了交叉互补与容错降级：
1. **Trip.com 国际站低价日历接口 (`hk.trip.com`)**：单次请求秒级获取全周期任意日期对的直飞往返含税底价（人民币 `CNY`），尤其擅长捕获 Google Flights 隐藏报价的国内全服务航司特惠票（如吉祥航空、东方航空含 `2×23kg` 免费托运行李的特价票）。
2. **春秋航空底层实时查价接口 (`hk.ch.com`)**：直连 `Flights/SearchByTime` 获取春秋航空 (`9C`) 与春秋日本 (`IJ`) 的实时票面价、税费明细及手提/托运行李额（绕过趋势接口 `MinPriceTrends` 返回 `null` 假售罄的坑）。
3. **Google Flights (`ds:1` 内嵌数据包)**：直接提取全球全服务航司与廉航的直飞航班号、起降时间、执飞机型与往返含税总价。

---

### 2. 目录结构
```text
.
├── LICENSE
├── README.md
├── skills/
│   └── multi-agent-flight-search/
│       ├── SKILL.md                        # Agent 技能定义（触发词、标准5步流程、防坑指南、核验标准）
│       └── scripts/
│           └── flight_query_helper.py      # 零外部依赖的 Python 3 实时查价脚本
└── examples/
    ├── shanghai_japan_top5_flights_report.md   # 示例报告：上海直飞日本全境（周一出发5天4晚）Top 5
    └── shanghai_korea_top5_flights_report.md   # 示例报告：上海直飞韩国全境（周一出发5天4晚）Top 5
```

---

### 3. 快速上手 (How to Use)

#### 方式一：作为 AI Agent 技能自动触发（推荐）
1. **安装技能到本地 Agent 目录**：
   ```bash
   # 安装到 Pi Agent 全局技能目录：
   mkdir -p ~/.pi/agent/pi-hermes-memory/skills/
   cp -r skills/multi-agent-flight-search ~/.pi/agent/pi-hermes-memory/skills/

   # 或安装到通用 ~/.agents/skills/ 目录：
   mkdir -p ~/.agents/skills/
   cp -r skills/multi-agent-flight-search ~/.agents/skills/
   ```
2. **自然语言一句话触发**：
   安装后，在任何对话中直接输入类似指令即可自动触发多 Agent 并行搜索：
   - *“搜索一下未来 3 个月从上海去日本任意城市 5 天行程最便宜的机票，周一出发，看一下特价票”*
   - *“用多 agent 搜一下未来 3 个月去韩国最便宜的机票组合”*
   - *“帮我查航班比价：下个月上海飞东南亚，周四出发玩 4 天，找最便宜的 Top 5 直飞往返”*

3. **触发后 Agent 自动执行的 5 步标准工作流**：
   - **第 1 步（构建日期×航线矩阵）**：自动计算时间窗口内所有符合条件的（去程日期, 返程日期）组合及目标机场列表。
   - **第 2 步（多 Agent 分片区并行检索）**：按地理片区（如日本拆分为「关东」、「关西+中部」、「九州+北海道+其他」；韩国拆分为「济州」、「首尔」、「釜山及地方」）并行派发 3~4 个子 Agent 同步扫描。
   - **第 3 步（三源互补与异常降级）**：自动整合 `trip_calendar` + `ch_day` + `gflights`，内置请求频控间隔与重试机制。
   - **第 4 步（交叉核验与行李审计）**：核实去返程精确航班号、起降航站楼，严格区分「廉航仅 7kg 手提裸票」与「全服务航司含 1~2 件 23kg 免费托运行李」。
   - **第 5 步（生成双视角报告）**：同时输出**【跨城市/航司代表性 Top 5 推荐榜】**、**【严格按绝对低价排序的 Top 10 速览表】**与**【全周期×各目的地最低价全景表】**。

#### 方式二：直接通过命令行运行查询脚本 (`flight_query_helper.py`)
脚本仅依赖 **Python 3.8+ 标准库**，无需安装任何第三方依赖包：

```bash
# 查看帮助说明
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py --help

# 1. 查询 Trip.com 直飞往返低价日历（例：上海 SHA -> 名古屋 NGO，从 2026-11-11 起 90 天，周一=0 出发，5 天行程）
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py \
  trip_calendar SHA NGO 2026-11-11 90 0 5

# 2. 查询春秋航空官网单日实时直飞含税价与税费/行李明细（例：上海浦东 PVG -> 济州岛 CJU）
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py \
  ch_day PVG CJU 2026-11-16

# 3. 查询 Google Flights 全航司直飞往返航班与含税价格（例：上海浦东 PVG -> 首尔仁川 ICN）
python3 skills/multi-agent-flight-search/scripts/flight_query_helper.py \
  gflights PVG ICN 2026-11-30 2026-12-04
```

---

### 4. 安全与隐私声明 (Security & Privacy)
- **无任何密钥或凭证泄漏风险**：本技能及脚本仅通过 `HTTPS` 访问公开、免登录的只读机票查询接口，不包含、不读取、也不存储任何 API Key、密码、Token、Cookie 或个人隐私路径。
- **严格的输入参数校验**：所有传入的机场/城市三字码（正则校验 `^[A-Za-z]{3}$`）与日期（严格校验 `YYYY-MM-DD`）均经过白名单验证与 URL 编码，杜绝参数注入风险。
- **零第三方依赖**：核心查询脚本完全基于 Python 3 标准库实现，无任何第三方供应链依赖风险。

---

## 📄 License
Apache License 2.0 — see [LICENSE](./LICENSE) for details.
