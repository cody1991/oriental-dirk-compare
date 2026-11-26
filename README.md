# 惊奇东方行优惠看板

给 Cody 自己用的惊奇东方行（Amazing Oriental）优惠看板：把官网当前优惠做成一页，方便按分类浏览、搜索和比较价格。

公开页面：https://cody1991.github.io/oriental-dirk-compare/

**不是** Amazing Oriental 或 Dirk 的官方网站、传单或 App。样式参考了 Cody 的 [Dirk 优惠看板](https://cody1991.github.io/dirk-offers-dashboard/)。

## 页面里有什么

- Weekly Deals、Amazing Deals、Mega Deals、鱼和肉（Vis en vlees）四个官方分类
- 中文商品名、现价与划线原价（没有原价的不当折扣）、有效期、商品图和官网链接
- 按折扣、单位价或售价排序，以及关键词搜索

优惠来自全连锁官网 https://amazingoriental.com/aanbiedingen/ ，Almere 分店（Metropolestraat 64）有没有货要到店才知道。

## 数据

用 `scripts/build_offers.py` 解析官网优惠页 HTML，生成 `data/offers.json`。本页是查阅时的快照，不会自动刷新。

当前这批数据查阅于 2026-11-27 凌晨（欧洲/阿姆斯特丹）：

- Weekly Deals：2026年11月25日–12月1日
- Amazing Deals、Mega Deals 与鱼和肉：2026年11月18日–12月8日

## 本地预览

```bash
python3 -m http.server 4176
```

然后打开 http://127.0.0.1:4176/
