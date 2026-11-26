# 东方行对照 Dirk

这是给 Cody 自己用的购物对照页，用来比较惊奇东方行（Amazing Oriental Almere）和本周 Dirk Almere 的优惠。

**不是** Amazing Oriental 或 Dirk 的官方网站、传单或 App。

公开页面：https://cody1991.github.io/oriental-dirk-compare/

## 这一页解决什么

不会煮菜、偏好即食或稍微加热时，本周该在东方行拿什么，哪些可以留给 Dirk。

- 东方行优先：肉柜现成烤五花、烤猪肉、烤排骨（没有原价，不当折扣），以及打折的 Lucky Duck 烤鸭；再带糯米鸡、烧卖、虾云吞等加热即食的冷冻货。
- 方便面和寿司这周交给 Dirk 更合适。
- 东方行优惠来自全连锁官网，Almere 店有没有货要到店才知道。

## 数据

- 东方行：https://amazingoriental.com/aanbiedingen/（2026-11-26 晚上查阅）
  - Weekly Deals：2026年11月25日–12月1日
  - Amazing Deals 与肉柜栏目 Vis en vlees：2026年11月18日–12月8日
- Dirk：本地看板快照 `offers.json`，`generatedAt` 为 2026-11-26T09:08:37.716Z，有效期 11月25日–12月1日
- Dirk Almere 店页：https://www.dirk.nl/winkels/almere/schipperplein/69
- Dirk 优惠看板：https://cody1991.github.io/dirk-offers-dashboard/

本仓库是独立站点，不修改 `dirk-offers-dashboard`。

## 本地预览

任意静态服务器即可，例如：

```bash
python3 -m http.server 4176
```

然后打开 http://127.0.0.1:4176/
