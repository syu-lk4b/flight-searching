---
name: "multi-agent-flight-search"
description: "使用多Agent并行搜索各大航空公司与比价平台，查找最便宜机票组合（含税总价、直飞/往返、特定出发星期与行程天数、跨多目的地比价、特价票检索）。当用户提到“搜机票”、“找便宜机票”、“特价机票”、“最便宜的机票组合”、“多agent搜机票”、“查航班”、“机票比价”、“飞日本/韩国/某地最便宜机票”、“flight search”、“cheap flights”时触发。"
version: 3
created: "2026-10-21"
updated: "2026-11-11"
---
## When to Use
当用户要求搜索跨日期、跨城市、跨航空公司的最便宜机票组合或特价票（例如“未来N个月从某地出发去某国/某地区任意城市、特定星期出发X天行程的最便宜Top N机票”），或需要使用多Agent并行比价各大航司与OTA平台时使用。

## Procedure
1. 第1步：明确约束与生成日期-航线矩阵。确认出发地机场（如上海 PVG/SHA）、目的地国家/城市范围（如日本全境、韩国全境、东南亚等）、时间窗口（如未来3个月）、出发星期与停留天数（如周一去周五回5天4晚，若用户未指明出发星期可简短确认或默认按周一出发5天4晚）、是否仅限直飞同城往返。
2. 第2步：调用技能目录下的可复用查询脚本 `scripts/flight_query_helper.py`（相对于 SKILL.md 所在目录）。支持三条标准子命令：(A) `python3 scripts/flight_query_helper.py trip_calendar <DEP_CITY> <ARR_CITY> <START_DATE> <SPAN_DAYS> <WEEKDAY_0_MON> <TRIP_DAYS>` 获取 Trip.com 直飞往返含税底价日历；(B) `python3 scripts/flight_query_helper.py ch_day <DEP> <ARR> <YYYY-MM-DD>` 获取春秋航空 (9C/IJ) 单程直飞实时含税价、税费及行李额（往返需分别查去程日和返程日相加）；(C) `python3 scripts/flight_query_helper.py gflights <DEP> <ARR> <DEP_DATE> [RET_DATE]` 获取 Google Flights 全航司（含全服务与廉航）直飞航班号、起降时间、机型与往返含税总价。
3. 第3步：按目的地片区拆分子 Agent 并行检索（可使用 subagent 或 acp_delegate 的 researcher 角色并行派发 3~4 个片区子 Agent）。例如日本拆分为「关东 NRT/HND/IBR」、「关西+中部 KIX/NGO/KMQ/FSZ」、「九州+北海道+其他 FUK/CTS/OKA/HIJ/TAK」；韩国拆分为「济州 CJU」、「首尔 ICN/GMP」、「釜山及地方 PUS/CJJ/TAE/MWX」。每个子 Agent 扫描全部日期对并将结构化数据写入独立 JSON 文件。
4. 第4步：主 Agent 汇总排序与交叉核验。主 Agent 读取各片区 JSON，按人民币（CNY）往返含税总价从低到高排序；对排名前列的特价候选组合，核实去返程精确航班号、起降时刻、航站楼及免费托运行李政策（严格区分廉航 7kg~10kg 手提裸票与全服务航司 1~2×23kg 免费托运行李）。必要时通过 Playwright 无头浏览器加载 hk.trip.com 对应日期直飞列表页做二次核验。
5. 第5步：生成双视角最终报告并落盘保存。同时输出：【主榜：跨城市/航司代表性最便宜 Top 5 机票组合（含日期、航班号、时刻、航站楼、含税价、行李额、核验链接）】、【附榜：不限城市去重的严格绝对最低价 Top 10 速览表】、【全周期×各目的地最低价全景对比表】及【出行购票实操建议（极致低价 vs 含托运行李性价比之王）】。

## Pitfalls
- 国内OTA（携程国内站 ctrip.com、飞猪、去哪儿）及全日空/日航/东航等航司官网预订接口有强滑块验证码或瑞数/Akamai WAF拦截，切勿直接用裸HTTP硬爬或陷入验证码死循环；应优先使用 hk.trip.com（国际版）+ Google Flights + 春秋官网 hk.ch.com 组合绕过。
- 春秋航空官网 hk.ch.com 的低价趋势接口（/Flights/MinPriceTrends）对东京(TYO)、福冈(FUK)等热门航线常返回 Price: null（假售罄），必须直接调用底层的 /Flights/SearchByTime 接口（即 scripts/flight_query_helper.py ch_day）获取真实含税价（MinCabinPrice 即为含税单程总价，RouteTotalTax 为税费明细）。
- 春秋官网 /Flights/SearchByTime 接口对高频并发请求敏感，连续快速请求会触发 Read Timeout 或返回空数组 Route: []；批量扫描日期时必须设置 0.5~1 秒间隔并对空结果做单次重试确认。
- Google Flights 的 URL 查询参数 ?q= 应使用标准格式 'nonstop+flights+from+<DEP>+to+<ARR>+<DDATE>+to+<RDATE>'（已内置于 scripts/flight_query_helper.py gflights），并在解析 AF_initDataCallback(ds:1) JSON 时用 len(legs) == 1 过滤直飞，且注意整点分钟数在 JSON 中可能为 null（需用 (arr[1] or 0) 格式化）。
- Google Flights 对部分中国航司（如吉祥航空 HO、上海航空 FM、国航 CA 的部分班次）或接口波动期只返回航班号与时刻但价格字段为 None；必须结合 Trip.com 日历接口、春秋官网实时接口或 Playwright 渲染 hk.trip.com 列表页补全特惠底价（例如吉祥航空常出现含 2×23kg 托运行李却比廉航裸票更便宜的隐藏神价）。
- 当 hk.trip.com GetLowPriceInCalender 接口偶发返回空（validStatus: null）时，子 Agent 应自动使用 ch_day + gflights 实时结果，并可结合 Playwright 渲染 hk.trip.com 航班列表页或同项目下的近期核验存档交叉兜底，避免空跑。

## Verification
1. 核实所有上榜 Top 5 组合均严格符合用户的出发/返程星期、行程天数、直飞同城往返等硬性条件。
2. 核实每一条推荐均包含完整字段：排名、人民币往返含税总价、去返程日期与起降时间、起降机场及航站楼、执飞航司与去返程航班号、手提与免费托运行李额说明、可复核的数据源 URL。
3. 确认全服务航司（如吉祥、东航、南航、国航、日航、全日空、大韩、韩亚）与廉航（如春秋、乐桃、捷星、济州航空）均已被覆盖比价，未因单一数据源遗漏含托运行李的全服务特价票。