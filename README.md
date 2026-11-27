# 惊奇东方行优惠看板

给 Cody 自己用的惊奇东方行（Amazing Oriental）优惠看板：把官网当前优惠做成一页，方便按分类浏览、搜索和比较价格。

公开页面：https://cody1991.github.io/oriental-dirk-compare/

**不是** Amazing Oriental 或 Dirk 的官方网站、传单或 App。样式参考了 Cody 的 [Dirk 优惠看板](https://cody1991.github.io/dirk-offers-dashboard/)。

## 页面里有什么

- Weekly Deals、Amazing Deals、Mega Deals、鱼和肉（Vis en vlees）四个官方分类
- 中文商品名、现价与划线原价（没有原价的不当折扣）、有效期、商品图和官网链接
- 官方只写「2 件 €x」「买 3 送 1」这类活动时，按原文保留，不自行换算单价
- 按折扣、单位价或售价排序，以及关键词搜索

优惠来自全连锁官网 https://amazingoriental.com/aanbiedingen/ ，Almere 分店（Metropolestraat 64）有没有货要到店才知道。

Almere 分店营业时间来自官方店页：https://amazingoriental.com/Location/winkels-almere/ 。数据里的 `store.closesAt`、`store.weeklyHours` 和 `store.upcomingHours` 都从该页解析，不以其他网站为准。某天休息会标成 `closed: true`。

## 每天怎么刷新并发布

仓库是静态页面，刷新数据后提交 `origin/main` 即可更新 GitHub Pages，没有额外构建步骤。不要提交 `node_modules`、`__pycache__` 或缓存目录。

一键流程（刷新 → 提交 → 推送 → 核对公开页）：

```bash
cd /workspace/oriental-dirk-compare
./scripts/publish-offers.sh
```

只更新本地数据、不推送时：

```bash
python3 scripts/refresh-offers.py
```

刷新脚本会下载官网优惠页 HTML 再解析（不只靠 Markdown，以免品名缺失），并同时读取 Almere 官方店页，写入 `data/offers.json`。提交信息形如 `Refresh Amazing Oriental offers for 2026-11-27`。推送后脚本会 `curl` 公开页和 `data/offers.json`，确认 HTTP 200，且线上 `generatedAt` 已更新。

中文名、包装和加热提示放在 `data/translations.json`。新品还没有中文名时，脚本会保留官网品名并在标准错误里列出，不会中断刷新，也不编造译名。

## 关店提醒标记

关店提醒使用仓库根目录的 `.ao-close-reminder-sent-YYYY-MM-DD`，不要和 Dirk 仓的 `.close-reminder-sent-*` 混用。刷新和发布脚本不会发送提醒，也不会删除这类标记。

## 本地预览

```bash
python3 -m http.server 4176
```

然后打开 http://127.0.0.1:4176/
