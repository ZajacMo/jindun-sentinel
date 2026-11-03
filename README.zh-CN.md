简体中文版本，英文原文见 [README.md](README.md)。

# JinDun Sentinel

金盾哨兵（JinDun Sentinel）是一个开源系统，用于同时监测多个经济体的系统性金融风险。它把公开的日频统计序列转换成每个经济体可复现的压力指数，判断该经济体当前处于平静区制（calm regime）还是压力区制（stressed regime）以及各自的概率，估计压力由哪些子市场、哪些国家向哪些对象传导，并在越过预先声明的阈值时发出少量分级预警（graded alerts）。它要解决的问题是：系统性风险的度量通常被拆散成互不兼容的几块——只有指数却没有解释它的区制模型，只有区制模型却没有说明谁在污染谁的网络，以及无法复现的仪表盘，因为它展示的数字没人能追溯到来源。金盾哨兵把整条链路作为一条流水线交付：每个对外发布的数字前面都有明确的质量门禁（quality gate），后面都有运行清单（run manifest）。

## 每日运行链路

下面每个阶段都由 `jindun-pipeline run` 执行。质量门禁位于计算的*前面*而不是后面：门禁不通过就会驳回该序列并阻断本次运行，因此不可用的输入永远不可能进入对外发布的指数。

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 470" width="100%" role="img" aria-labelledby="jd-title jd-desc">
  <title id="jd-title">金盾哨兵每日流水线</title>
  <desc id="jd-desc">外部数据源由各适配器读取，读取结果送入质量门禁。质量门禁不通过会驳回该序列并阻断运行。通过门禁的序列经过标准化、按子市场做 PCA 降维、合成为 MBSED 综合压力指数、判定压力区制、转化为溢出网络并进行预警判定。最终产物由 FastAPI 应用对外提供，并由 Web 前端渲染。</desc>

  <g fill="none" stroke="#57606a" stroke-width="1.6" stroke-linecap="round">
    <path d="M240 67 H262" />
    <path d="M470 67 H492" />
    <path d="M700 67 H722" />
    <path d="M930 67 H952" />
    <path d="M1060 94 V241" />
    <path d="M960 277 H938" />
    <path d="M730 277 H708" />
    <path d="M500 277 H478" />
    <path d="M300 304 V342 H140 V371" />
    <path d="M240 407 H262" />
  </g>
  <g fill="#57606a">
    <polygon points="270,67 261,62 261,72" />
    <polygon points="500,67 491,62 491,72" />
    <polygon points="730,67 721,62 721,72" />
    <polygon points="960,67 951,62 951,72" />
    <polygon points="1060,250 1055,241 1065,241" />
    <polygon points="930,277 939,272 939,282" />
    <polygon points="700,277 709,272 709,282" />
    <polygon points="470,277 479,272 479,282" />
    <polygon points="140,380 135,371 145,371" />
    <polygon points="270,407 261,402 261,412" />
  </g>

  <g fill="none" stroke="#cf222e" stroke-width="1.6" stroke-dasharray="5 4" stroke-linecap="round">
    <path d="M600 94 V141" />
  </g>
  <polygon points="600,150 595,141 605,141" fill="#cf222e" />
  <text x="612" y="128" font-family="sans-serif" font-size="11" fill="#cf222e">门禁不通过</text>

  <g fill="#f6f8fa" stroke="#57606a" stroke-width="1.4">
    <rect x="40" y="40" width="200" height="54" rx="6" />
    <rect x="270" y="40" width="200" height="54" rx="6" />
    <rect x="500" y="40" width="200" height="54" rx="6" />
    <rect x="730" y="40" width="200" height="54" rx="6" />
    <rect x="960" y="40" width="200" height="54" rx="6" />
    <rect x="960" y="250" width="200" height="54" rx="6" />
    <rect x="730" y="250" width="200" height="54" rx="6" />
    <rect x="500" y="250" width="200" height="54" rx="6" />
    <rect x="270" y="250" width="200" height="54" rx="6" />
    <rect x="40" y="380" width="200" height="54" rx="6" />
    <rect x="270" y="380" width="200" height="54" rx="6" />
  </g>

  <g fill="#fff8c5" stroke="#cf222e" stroke-width="1.4">
    <rect x="460" y="150" width="280" height="54" rx="6" />
  </g>

  <g font-family="sans-serif" font-size="10" font-weight="bold" fill="#57606a">
    <text x="53" y="58">1</text>
    <text x="283" y="58">2</text>
    <text x="513" y="58">3</text>
    <text x="743" y="58">4</text>
    <text x="973" y="58">5</text>
    <text x="973" y="268">6</text>
    <text x="743" y="268">7</text>
    <text x="513" y="268">8</text>
    <text x="283" y="268">9</text>
    <text x="53" y="398">10</text>
    <text x="283" y="398">11</text>
    <text x="473" y="168" fill="#cf222e">&#215;</text>
  </g>

  <g font-family="sans-serif" font-size="13" font-weight="bold" fill="#1f2328" text-anchor="middle">
    <text x="140" y="64">外部数据源</text>
    <text x="370" y="64">适配器</text>
    <text x="600" y="64">质量门禁</text>
    <text x="830" y="64">标准化</text>
    <text x="1060" y="64">子市场 PCA</text>
    <text x="1060" y="274">MBSED 综合压力指数</text>
    <text x="830" y="274">区制识别</text>
    <text x="600" y="274">溢出网络</text>
    <text x="370" y="274">预警</text>
    <text x="140" y="404">FastAPI</text>
    <text x="370" y="404">Web 界面</text>
    <text x="600" y="174" fill="#cf222e">已驳回</text>
  </g>

  <g font-family="sans-serif" font-size="10.5" fill="#57606a" text-anchor="middle">
    <text x="140" y="82">ECB, BIS, BOJ, FSB, akshare</text>
    <text x="370" y="82">只读，快照缓存</text>
    <text x="600" y="82">陈旧度、缺口、边界</text>
    <text x="830" y="82">按方向的 cdf_rank</text>
    <text x="1060" y="82">eigh，80% 方差</text>
    <text x="1060" y="292">加权相关型</text>
    <text x="830" y="292">MS-AR，滤波后验</text>
    <text x="600" y="292">paper / Sims / DY / legacy</text>
    <text x="370" y="292">P1 / P2 / P3 规则</text>
    <text x="140" y="422">/api/v1，文档在 /api/docs</text>
    <text x="370" y="422">Vue 3，四种语言</text>
    <text x="600" y="192" fill="#cf222e">该序列被排除，运行以 1 退出</text>
  </g>
</svg>

## 本项目不是什么

综合性系统风险指数的学术实现通常只是研究产物：输入序列来自商业终端，代码只在某一位作者的一台机器上、针对一个工作簿运行，公布的表格也无法重新生成。商业风险平台恰好相反：它们可复现、始终在线，但封闭、收费，而且发布指数时不附带解释它的模型。仪表盘类项目通常从一个已经算好的指数出发，能以多种语言展示它，却无法复现它。

金盾哨兵正是为了补上这一缺口而构建的，而且它的主张刻意保持狭窄：目前不存在一个免费、经过核验、日频、跨国的系统，能够把溢出网络（spillover network）、区制概率模型和早期预警闭环作为同一条可运行流水线一并交付。

| | 学术复现 | 商业终端流水线 | 仪表盘项目 | JinDun Sentinel |
| --- | --- | --- | --- | --- |
| 输入免费且可公开核验 | 否 | 否 | 不适用 | 是，各来源的覆盖范围见下文 |
| 日频、跨国 | 否 | 是 | 否 | 是 |
| 传染 / 溢出网络 | 通常 | 有时 | 很少 | 是，四种估计量 |
| 区制概率模型 | 有时 | 是 | 很少 | 是，经滤波与估计 |
| 带分级预警的早期预警闭环 | 否 | 是 | 否 | 是，声明式规则 |
| 能够阻断运行的质量门禁 | 否 | 否 | 否 | 是，逐序列判定 |
| 运行清单（代码版本、数据批次、哈希） | 否 | 否 | 否 | 是 |
| 服务端与前端使用同一份语言目录 | 不适用 | 不适用 | 通常 | 是，四种语言 |

## 四个层次

| 层次 | 计算内容 | 方法 | 产物 / 端点 |
| --- | --- | --- | --- |
| 国家层指数 | 每个子市场（股票、债券、外汇、货币、衍生品）各一个压力指数，以及 MBSED 综合压力指数（composite），以两种口径报告 | 按方向的 `cdf_rank` 标准化，子市场 PCA（`numpy.linalg.eigh`，取累计解释方差达到 80 % 的最小成分个数），CRITIC 或配置的权重，综合指数 `sqrt((W ⊙ s) P (W ⊙ s)' × 2)`，百分位（percentile）与偏离趋势（deviation）两种口径 | `data/runs/<CC>/market_indices.csv`、`run.json`；`GET /api/v1/countries/{code}/index` |
| 区制 | 每个观测值所属的压力区制（中等 / 高）及其概率 | 对对数综合指数做马尔可夫切换自回归（2 个状态，5 阶，状态依赖方差，趋势项 `c`），使用**滤波后验**概率，并提供确定性的双簇回退方案；双成分正态混合，其位置与离散度由拟合结果估计 | `run.json` → `regime` 块；`GET /api/v1/countries/{code}/index` |
| 传染 | 有向的跨市场溢出网络：自身风险占比、总溢出量、总传入量、净溢出方 | VAR 配合 BIC 阶数选择（最高 5 阶），以及预测误差方差分解的四种广义化之一；按行归一化的占比 | `run.json` → `spillover` 块；`GET /api/v1/countries/{code}/spillover` |
| 全球 | 跨国传染、全球金融周期因子、跨境银行网络与 G-SIB 名单 | 同样把广义方差分解应用于国家综合指数（仅使用共同的日历区间）、对一组经过标准化的 BIS 全球流动性、信用缺口与有效汇率序列做第一主成分（并把国别面板的第一主成分作为交叉验证一并发布）、BIS 银行机构统计、FSB G-SIB 文件 | `data/runs/global/*.json`；`GET /api/v1/global/spillover`、`/global/cycle`、`/global/banking-network`、`/global/gsib` |

四种溢出估计量（estimator）不可互换，每一种都有各自的注意事项：

| 方法 | 是什么 | 是否依赖阶数 | 是否带符号 | 是否为默认 |
| --- | --- | --- | --- | --- |
| `paper_equation` | 来源规范中的公式 (6) 与 (7) | 否 | 否 | **是** |
| `sims_structural` | Sims (1980) FEVD，Cholesky 正交化 | 是 | 否 | 否 |
| `dy_generalised` | Diebold-Yilmaz (2009, 2012) 广义 FEVD | 否 | 是 | 否 |
| `legacy_appendix` | 此前发布代码的字面转写；一个基于残差相关性的加权指数，**不是**方差分解 | 否 | 否 | 否 |

完整对比见 `docs/methodology/spillover-legacy-vs-paper.md`。

**四种估计量在每份产物中都会发布**，并列放在 `spillover.estimators` 之下；默认的那一种同时内联在 `spillover` 本体中，供不需要做选择的调用方使用。对于某个网络无法计算的估计量，会连同原因一起列在 `spillover.failed_estimators` 中——它不会影响其余估计量。API 通过显式参数接收选择（`?method=…`），如果请求的估计量产物中并未发布，就返回 `400` 并列出实际发布的估计量，因此一个请求永远不会得到与所请求不同的估计量。

## 经济体与语言

在范围内的经济体共有五个。它们**不是**用同一种工具度量的，`docs/methodology/country-profiles.md` 明确写清了每个经济体具备什么、不具备什么。

| 经济体 | 代码 | 国家指数 | 交叉核验锚点 | 是否随附配置 | 本仓库是否已发布运行结果 |
| --- | --- | --- | --- | --- | --- |
| 中国 | `CN` | 覆盖五个市场的 MBSED 综合压力指数 | ECB CISS 日频综合指数 `SS_CIN`（区域 `CN`） | 是 — `packages/pipeline/configs/countries/cn.yaml` | 是 |
| 日本 | `JP` | 覆盖两个市场（BOJ 拆借利率、美元兑日元）的 MBSED 综合压力指数 | **无** — ECB CISS 完全没有发布任何日本序列 | 是 — `configs/countries/jp.yaml` | 是 |
| 美国 | `US` | 官方 ECB 综合压力指数 | 该指数本身（`SS_CIN`，区域 `US`） | 是 — `configs/countries/us.yaml` | 是 |
| 英国 | `GB` | 官方 ECB 综合压力指数 | 该指数本身（`SS_CIN`，区域 `GB`） | 是 — `configs/countries/gb.yaml` | 是 |
| 欧元区 | `EU` | 官方 ECB 综合压力指数 | 该指数本身（`SS_CIN`，区域 `U2`） | 是 — `configs/countries/eu.yaml` | 是 |

如果某个经济体的指数本身就是官方发布的指数，它就**没有**子市场分解，因而也没有市场归因和跨市场溢出网络：运行产物会明确写出这一点，而不是发布一个从未真正计算过的分解。这被当作**数据**而不是错误来陈述：每份产物都带有 `profile` 和 `capabilities` 映射，API 与前端都会读取它们，因此这种缺失被呈现为该经济体的一项属性，而不是一次失败。跨国网络和全球周期因子作用于国家综合指数，因此对五个经济体都可用。

随附的四种语言为英语（`en-US`）、简体中文（`zh-CN`）、繁体中文（`zh-TW`）和日语（`ja-JP`）。简体与繁体中文均为人工撰写而非机器转换，因为两者的金融术语确实存在差异。`locales/` 下的语言目录文件是唯一事实来源：Python 服务端通过 `jindun.i18n` 读取它们，前端在构建时通过一个 Vite 插件读取完全相同的文件。

## 数据覆盖

下表中每一条覆盖范围说明，都来自对应适配器自己文档字符串中的记录，即当时对在线服务核验的结果。“已知缺口”一列最为关键：一个隐藏自身缺口的实现是无法被监测的。

| 来源 | 端点 / 格式 | 覆盖范围 | 已知缺口与限制 |
| --- | --- | --- | --- |
| ECB CISS — 日频综合指数 `SS_CIN` | `https://data-api.ecb.europa.eu/service/data/CISS/D.<area>.Z0Z.4F.EC.SS_CIN.IDX?format=csvdata&detail=dataonly`（SDMX 2.1；键是**一个**路径段，各维度之间用点分隔） | 14 个参考区域：`AT BE CN DE ES FI FR GB IE IT NL PT U2 US` | 日频下不存在其他参考区域，日本也不例外 |
| ECB CISS — 月频综合指数 `SS_CI` | 同一基础路径，改为 `M.<area>.…` 与 `SS_CI` | 2 个参考区域：`U2`、`US` | 任何单个成员国都**没有**发布月频综合指数 |
| ECB CISS — 子压力分项 | `…/D.<area>.….<COMPONENT>_CON/CON` | 5 个分项（`CREDIT`、`EQUITY`、`INTERBANK`、`REAL_ESTATE`、`SOVEREIGN`），仅适用于欧元区 `U2` | 分项只以 `.CON` 贡献度序列的形式存在；分项的 `.IDX` 变体并不存在，请求会返回 404。`CN`、`GB`、`US` 不提供分项数据 |
| ECB CISS — 日本 | 任意日本参考区域 | **无** | 所有日本参考区域在日频与月频下均返回 404。因此日本**没有 CISS 交叉核验锚点**，改用日本银行的 API，并在方法说明中明确写出这一点 |
| BIS 统计 API — 数据 | `https://stats.bis.org/api/v1/data/{flow}/{key}?startPeriod=…&endPeriod=…&format=csvfile` | 已发布的 56 个数据流中使用 10 个：`WS_LBS_D_PUB`、`WS_LBS_PUB`、`WS_CBS_PUB`、`WS_GLI`、`WS_CREDIT_GAP`、`WS_DSR`、`WS_EER`、`WS_XRU`、`WS_OTC_DERIV2`、`WS_CPP` | **键必须放在 URL 路径中。**形如 `/api/v1/data/WS_LBS_D_PUB?key=…` 的请求会静默忽略该键并返回整个数据流——仅一个季度的银行机构统计就有 25 MB，而同样的查询写成路径形式只有 358 字节 |
| BIS 统计 API — 结构 | `https://stats.bis.org/api/v1/dataflow/BIS`（SDMX-ML） | 完整的数据流目录 | 请求 JSON 表示（`Accept: application/vnd.sdmx.structure+json`）会返回 **406**；该端点提供的是 SDMX-ML XML，适配器解析的正是这一格式 |
| BIS 批量归档 — 银行机构统计 | `https://data.bis.org/static/bulk/WS_LBS_D_PUB_csv_flat.zip`（365 MB，解压后约 18 GB） | 报告经济体 × 交易对手国家的双边矩阵 | **双边矩阵只由批量文件提供。**通过 API 访问时，报告国家维度只接受汇总值 `5A`，因此请求 `L_REP_CTY=US` 会返回 404，尽管数据已经发布。归档文件会一次性下载到 `data/cache/`（不提交到仓库），再流式过滤为 `data/snapshots/bis/` 下约两兆字节的快照（下载获取，不提交到仓库） |
| BIS 批量归档 — 全球流动性、信用缺口与有效汇率 | `https://data.bis.org/static/bulk/{WS_GLI,WS_CREDIT_GAP,WS_EER}_csv_flat.zip`（0.2 MB、0.2 MB 与 6.3 MB） | 全球金融周期因子的输入 | SDMX API 只提供这几个流的汇总值，而不提供该因子所需的维度组合，因此窄 key 请求会返回 404，批量文件是唯一可行的途径。`WS_EER` **同时**包含日频块与月频块，二者在日历时间上重叠：只能读取日频块，否则同一个季度里会混进一个月度均值和一个日度观测。每个流的最后一个季度都只发布了一半，必须排除 |
| BIS SDMX v2 | `/api/v2/…` | 无 | v2 路径返回 **404** 或 **501**；只存在 v1 API |
| 日本银行 — 时序统计检索 | `https://www.stat-search.boj.or.jp/api/v1/getMetadata`、`/getDataCode`、`/getDataLayer` | 本项目使用 10 个数据库：`IR01`、`FM01`、`FM02`、`FM08`、`FM09`、`MD01`、`MD02`、`PR01`、`CO`、`BP01`（适配器还支持 `BIS`，即 BIS 国际银行与信贷统计中的日本部分），另有四条派生序列（拆借利率期限利差、拆借利率离散度、美元兑日元波动率、美元兑日元趋势偏离） | `getDataCode` 每次请求最多接受 250 个序列代码，`getDataLayer` 最多 1 250 个；分页由 `NEXTPOSITION` 驱动，必须以 `startPosition` 原样回传；该服务要求客户端不要高频访问，因此适配器在两次请求之间强制设置最小间隔。日本银行不发布日频股票指数、日频衍生品市场和日频国债收益率曲线，所以日本指数只有两个市场而不是五个。日本指数使用的是拆借利率**离散度**而非期限利差：`FM02` 的期限拆借利率从 2025 年才开始，那会把日本指数的历史压缩到只剩两年 |
| FSB — G-SIB 名单 | 公告页面 → 链接的 PDF | 年度名单，解析为银行名称及 1–10 的分组 | 银行名称**不在**公告页面中：它们位于名单页面链接的 PDF 里，因此适配器会解析该链接并读取文档的文本层。分组附加资本按巴塞尔标准（每提高一个分组 0.5 %，1.0 %–5.0 %） |
| akshare — 中国市场数据 | `akshare` Python 包 | 登记在册的 26 条序列（14 条直接读取上游表格 + 12 条确定性派生）：上交所/深交所/沪深 300 指数点位与成交额、中债国债收益率与曲线斜率、SHIBOR 定盘价、融资余额、沪深 300 股指期货、美元兑人民币中间价 | `akshare` 是**可选**依赖（`--extra market`）。未安装时，每一项中国指标都会被报告为不可用并附带警告——绝不会静默地变成零。只有输出结构经过在线服务核验的序列才会登记 |

原始数据源为商业终端或研究构造的中国指标，在 `cn.yaml` 中保留并标注 `enabled: false`，而不是用代理指标替代，这样缺口始终可见：`pe_ratio`、`credit_risk_premium`、`bond_index_volatility`、`exchange_rate_distortion`。

## 安装

Python 端是一个 [uv](https://docs.astral.sh/uv/) 工作区：根目录的 `pyproject.toml` 将 `packages/*` 声明为成员，并从工作区依赖 `jindun-pipeline` 与 `jindun-api`。

```bash
uv sync --extra dev --extra market --all-packages
```

工作区成员是三个 Python 包（`packages/pipeline`、`packages/api`、`packages/agent`）；前端是独立的 npm 包，不在成员之列。

`jindun-pipeline` 可用的附加依赖组：`arch`（GARCH 波动率）、`market`（akshare）、`ml`（torch）、`dev`（pytest、pytest-cov、ruff、mypy）。`jindun-api` 提供一个 `dev` 附加依赖组，包含 pytest、httpx、ruff 和 mypy。

前端是独立的 npm 包，不属于 uv 工作区：

```bash
cd packages/web
npm install
npm run dev      # http://localhost:5173
```

## 快速开始

### 1. 查看适配器能提供什么

```bash
jindun-pipeline sources
```

以 JSON 形式输出：已配置的国家及其市场与指标数量、全部已登记的 akshare 序列、ECB CISS 参考区域、BIS 数据流以及日本银行的数据库。

### 2. 下载已配置的数据源

```bash
jindun-pipeline fetch                     # every enabled country
jindun-pipeline fetch --country CN        # one country (repeatable)
jindun-pipeline fetch --refresh           # ignore the snapshot cache
```

每个响应都会连同其 URL、获取时间和 SHA-256 一起写入快照库，因此后续运行可以基于相同的字节重放。只要有序列返回为空，该命令就会以 1 退出。

### 3. 运行流水线

```bash
jindun-pipeline run
jindun-pipeline run --country CN --out data/runs
jindun-pipeline run --refresh
```

按国家写入 `<out>/<CODE>/`：

| 文件 | 内容 |
| --- | --- |
| `market_indices.csv` | 各子市场的压力指数，每个市场一列 |
| `run.json` | 综合指数、百分位与偏离度序列，区制块，溢出网络（其中包含溢出激增预警背后的滚动溢出历史），预警，最近一次变动的归因，带走前验证得分的预测（forecast），来源清单与警告 |
| `quality.json` | 逐序列的质量门禁结论，含每项检查的实测值与阈值 |

每次运行还会生成一份清单 `<out>/manifest-<run_id>.json`，固定记录运行 ID、开始时间、git commit 与 dirty 标记、产物路径、耗时以及警告信息。只要任一国家的质量报告包含失败项，该命令就会以 1 退出。

五个经济体跑完一次约需三分钟。原本会占去大部分时间的两个环节被有意限制在固定规模：走前验证（walk-forward）评估只在有限个起点上重新拟合模型，区制模型与预测只使用最近的 2 500 个观测值。

### 4. 构建全球层

```bash
jindun-pipeline global
```

写出 `data/runs/global/spillover.json`（跨国网络）、`cycle.json`（全球金融周期因子）、`banking_network.json`（BIS 跨境银行网络）和 `gsib.json`（FSB G-SIB 名单）。周期因子由 BIS 的全球流动性、信用缺口与有效汇率序列估计得到，其方法与局限见 `docs/global/global-cycle-factor.md`。银行网络从 BIS 快照读取；生成该快照的方法见 `docs/global/banking-network.md`。

### 5. 不重算的情况下复核门禁

```bash
jindun-pipeline verify
jindun-pipeline verify --country CN
```

基于已保存的快照重新评估质量门禁，并以 JSON 形式输出报告。报告中出现失败项时以 1 退出。

### 6. 启动 API 服务

整个应用由两个进程构成——后端服务与前端——最省事的方式是一起启动：

```bash
python scripts/serve_dev.py
```

启动器会拉起两个进程，为各自的输出加上前缀流式打印，并在被中断时一并停止。此时 API 位于 `http://localhost:8000`，前端位于 `http://localhost:5173/`。

如需单独运行 API：

```bash
uvicorn jindun_api.app:app --reload --port 8000
```

OpenAPI 文档位于 `/api/docs`，schema 位于 `/api/openapi.json`。

| 端点 | 返回内容 |
| --- | --- |
| `GET /api/v1` | 服务名称、版本、文档位置 |
| `GET /api/v1/health` | 存活状态、存储中包含的国家、最近一次运行 ID |
| `GET /api/v1/run-metadata` | 产物根目录、国家、最近一次运行 ID 与开始时间 |
| `GET /api/v1/locales` | 服务端可渲染的语言以及回退语言 |
| `GET /api/v1/messages?locale=&key=` | 一条渲染后的消息，或整个语言目录 |
| `GET /api/v1/countries` | 存储中每个国家的一条摘要 |
| `GET /api/v1/countries/{code}/index?lens=percentile\|deviation\|composite` | 综合指数、两种口径、市场指数与区制块 |
| `GET /api/v1/countries/{code}/spillover` | 跨市场网络：节点、矩阵、溢出量、传入量、净溢出 |
| `GET /api/v1/countries/{code}/alerts` | 最近一次运行发出的预警 |
| `GET /api/v1/countries/{code}/data-quality` | 最近一次运行的质量结论 |
| `GET /api/v1/global/spillover` | 跨国网络 |
| `GET /api/v1/global/cycle` | 全球金融周期因子，附带其载荷与交叉验证 |
| `GET /api/v1/global/banking-network` | 跨境银行网络 |
| `GET /api/v1/global/gsib` | 带分组的 G-SIB 名单 |

API 是对流水线所写产物的只读视图：它绝不重算指数，因此屏幕上的数字就是清单里的数字。

服务器由三个环境变量配置：

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `JINDUN_RUNS_DIR` | 仓库中的 `data/runs` | 读取产物的位置 |
| `JINDUN_LOCALE_DIR` | 仓库中的 `locales/` | 读取共享语言目录的位置 |
| `JINDUN_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的浏览器来源 |

API 通过 `jindun.i18n` 暴露语言目录，后者读取共享的 `locales/` 目录。该目录是**被发现**的，而不是靠猜：仓库根目录是同时带有 `pyproject.toml` 和非空 `locales` 目录的最近上级目录，因此服务端与前端读取的始终是同一批文件。只有当语言目录位于别处时才需要设置该环境变量。

### 7. 让前端对接 API

```bash
cd packages/web
npm run dev
```

前端默认与 `http://localhost:8000` 通信；设置 `VITE_API_BASE` 可将其指向其他地址。

### 7b. 或者用容器跑起来

```bash
docker compose -f deploy/docker-compose.yml up --build
```

同样的两个服务，只是换成了镜像：API 在 <http://localhost:8000>，前端在 <http://localhost:5173/>。仓库的 `data/` 目录会挂载进 API 容器，因此在宿主机上跑出的流水线产物无需重新构建即可被读取。细节见 `deploy/README.md`。

### 8. 向系统提问

```bash
jindun-agent ask --question "How stressed is China?" --country CN --locale zh-CN
jindun-agent ask --question "Who lends to whom?" --json
jindun-agent tools
```

智能体读取与 API 相同的运行产物。没有配置 LLM 接口时，它以确定性方式、用所请求的语言作答；配置了 `JINDUN_LLM_BASE_URL`、`JINDUN_LLM_API_KEY` 和 `JINDUN_LLM_MODEL` 之后，它会向模型提问，提示词中带上已发布的数字，并要求模型不得编造数字。离线路径从不访问网络，它打印的每一个数字都出自某份产物。

## 仓库结构

```
jindun-sentinel/
├── pyproject.toml            uv workspace root (members: the three Python packages)
├── uv.lock                   resolved dependency lock
├── README.md                 this file
├── LICENSE                   Apache License 2.0
├── CHANGELOG.md              Keep a Changelog format
├── CONTRIBUTING.md           setup, standards, how to add a country
├── CODE_OF_CONDUCT.md        Contributor Covenant v2.1
├── SECURITY.md               vulnerability reporting
├── locales/                  shared message catalogues: en-US, zh-CN, zh-TW, ja-JP
├── deploy/                   the container setup: Dockerfiles, compose file, nginx
├── data/
│   ├── runs/                 published artefacts and run manifests
│   ├── snapshots/            raw source snapshots (fetched, not committed)
│   ├── baseline/             vendored regression baselines and their provenance
│   └── cache/                bulky reproducible downloads (not committed)
├── docs/
│   ├── methodology/          the spillover estimators, the country profiles
│   ├── global/               the global layer, the cycle factor and the banking network
│   └── user-guide/           the quick start
├── packages/
│   ├── pipeline/             jindun-pipeline — the computation core
│   │   ├── configs/          global.yaml and countries/*.yaml
│   │   ├── src/jindun/       indicators, index, regime, contagion, adapters, global_layer
│   │   └── tests/            pytest suite
│   ├── api/                  jindun-api — the FastAPI server
│   │   └── src/jindun_api/   app, store, schemas, routers
│   ├── agent/                jindun-agent — the question answering layer
│   │   └── src/jindun_agent/ context, tools, prompts, agent, cli
│   └── web/                  @jindun/web — the Vue 3 front end
│       └── src/              api client, stores, composables, components, i18n
└── scripts/                  the baseline freeze, the BIS download and extraction,
                             the locale tools and the local dev launcher
```

Python 包按层次组织，使每个阶段都能被单独测试和复用：`indicators`（指标变换）、`index`（标准化、PCA、CRITIC、综合指数）、`regime`（HP 滤波、马尔可夫切换、概率模型）、`contagion`（VAR、广义方差分解、激增检验）、`adapters`（只读数据源客户端）、`global_layer`（跨国层、全球周期、银行网络）。

承载全球层的包名为 `global_layer` 而不是 `global`：`global` 是 Python 关键字，`from .global import …` 无法解析。

## 本仓库的已知缺口

这里如实列出，因为一个隐藏自身缺口的监测系统是无法被监测的。

| 领域 | 状态 |
| --- | --- |
| 国家配置 | 五个经济体全部随附，其运行结果已在本仓库发布 |
| 日本指数 | 日本银行不发布日频股票指数、日频衍生品市场和日频国债收益率曲线，因此日本指数只有**两个**市场而不是五个，日本的跨市场溢出网络也只有两个节点。日本银行的月度与季度价格数据库没有混入日频面板 |
| 美国、英国与欧元区的子市场分解 | 这些经济体使用官方 ECB 综合压力指数度量，因此**没有**子市场分解、没有市场归因、也没有跨市场溢出网络。每份运行产物都会明确写出这一点 |
| 全球层产物 | `jindun-pipeline global` 会把四份产物写入 `data/runs/global/`；在该命令执行之前，`/api/v1/global/*` 端点返回 404 |
| BIS 归档 | 双边矩阵只由批量归档提供，该文件会一次性下载到 `data/cache/`（365 MB，不提交到仓库），再流式过滤为 `data/snapshots/bis/` 下约两兆字节的快照（不提交到仓库） |
| 来源规范中公布的表 5-2 | 它**无法**被精确复现：原始输入工作簿从未公开，对 4 696 个候选规格的穷举搜索也没有找到任何一个能复现它。`docs/methodology/spillover-legacy-vs-paper.md` 给出了相关证据以及取而代之的回归策略 |
| 静态分析 | 三个 Python 包的 `ruff check` 均无告警。`mypy` 在 pipeline 中仍报告 22 处问题——主要是适配器层的类型标注精度问题，其中没有已知的运行时缺陷 |
| 持续集成 | `.github/workflows/ci.yml` 在每次推送和拉取请求上运行代码检查、测试套件、语言目录审计以及前端的构建与测试 |

## 许可证

Apache License 2.0 —— 见 [LICENSE](LICENSE)。

## 参与贡献

环境搭建、编码规范、提交约定以及新增国家的流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。每个拉取请求都应保持 `pytest` 全部通过、不引入新的 `ruff` 或 `mypy` 问题，并让语言目录与前端保持同步。

## 问题反馈

- 缺陷与功能请求：请在仓库中提交 issue。
- 安全漏洞：**不要**公开提交 issue。请遵循 [SECURITY.md](SECURITY.md) 中的私下报告流程。
- 贡献代码：请先阅读 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)；它对参与本项目具有约束力。

## 致谢

本项目的方法沿用来源研究已公布的规范，包括方差分解的公式 (6) 与 (7)，以及 MBSED 综合压力指数的构造方式。已公布规范与此前发布实现之间的对比记录在 `docs/methodology/spillover-legacy-vs-paper.md`。
