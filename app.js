const euro = new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR" });
const dateFmt = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Europe/Amsterdam",
  dateStyle: "medium",
  timeStyle: "short"
});

const FILTERS = [
  { value: "全部", label: "全部" },
  { value: "Weekly Deals", label: "本周特价" },
  { value: "Amazing Deals", label: "Amazing Deals" },
  { value: "Mega Deals", label: "Mega Deals" },
  { value: "Vis en vlees", label: "鱼和肉" }
];

const SORTS = [
  { value: "discount", label: "折扣最高" },
  { value: "unit", label: "单位价低" },
  { value: "price", label: "售价最低" }
];

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function price(value) {
  return value == null ? "—" : euro.format(value);
}

function daysUntilValidTo(validTo) {
  if (!validTo) return null;
  const todayKey = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Amsterdam",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date());
  const toUtc = (dateKey) => {
    const [year, month, day] = dateKey.split("-").map(Number);
    return Date.UTC(year, month - 1, day);
  };
  return Math.round((toUtc(validTo) - toUtc(todayKey)) / 86400000);
}

function isAlmostExpired(offer) {
  const days = daysUntilValidTo(offer.validTo);
  return days != null && days >= 0 && days <= 1;
}

function matchesFilter(offer, category) {
  return category === "全部" || (offer.categories || [offer.category]).includes(category);
}

function sortOffers(offers, sortBy) {
  const unit = (item) => (item.unitPrice != null ? item.unitPrice : Number.POSITIVE_INFINITY);
  const sale = (item) => (item.sale != null ? item.sale : Number.POSITIVE_INFINITY);
  return [...offers].sort((a, b) => {
    if (sortBy === "unit") return unit(a) - unit(b) || (b.discountPercent ?? -1) - (a.discountPercent ?? -1);
    if (sortBy === "price") return sale(a) - sale(b) || (b.discountPercent ?? -1) - (a.discountPercent ?? -1);
    return (b.discountPercent ?? -1) - (a.discountPercent ?? -1) || (a.nameZh || a.name).localeCompare(b.nameZh || b.name, "zh");
  });
}

function card(offer) {
  const almost = isAlmostExpired(offer);
  const img = offer.imageUrl
    ? `<img src="${esc(offer.imageUrl)}" alt="${esc(offer.nameZh)}" loading="lazy" decoding="async" />`
    : "";
  const badge = almost
    ? '<span class="expiry-badge">即将结束</span>'
    : offer.promo
      ? `<span>${esc(offer.promo)}</span>`
      : "";
  const dutch = offer.name ? `<p class="original-name">${esc([offer.brand, offer.name].filter(Boolean).join(" · "))}</p>` : "";
  const validity = (offer.validityZh || offer.validityNl)
    ? `<p class="validity${almost ? " expiring" : ""}">${esc(offer.validityZh || offer.validityNl)}${offer.validityZh && offer.validityNl ? `<span class="validity-nl"> · ${esc(offer.validityNl)}</span>` : ""}</p>`
    : "";
  const pack = offer.packageZh || offer.package ? `<p class="pack">${esc(offer.packageZh || offer.package)}</p>` : "";
  const prep = offer.prep ? `<p class="pack">${esc(offer.prep)}</p>` : "";
  let priceRow;
  if (offer.sale == null && offer.promo) {
    priceRow = `<div class="price"><b>${esc(offer.promo)}</b></div>${offer.original != null ? `<span class="list-price">单件标价 ${price(offer.original)}</span>` : ""}`;
  } else {
    const original = offer.original != null ? `<s>${price(offer.original)}</s>` : "";
    const discount = offer.discountPercent ? `<i>−${esc(offer.discountPercent)}%</i>` : "";
    priceRow = `<div class="price"><b>${price(offer.sale)}</b>${original}${discount}</div>`;
  }
  const unit = offer.unitPrice != null ? `<span class="unit-price">${price(offer.unitPrice)}/kg</span>` : "";
  const product = offer.productUrl
    ? `<a class="product-link" href="${esc(offer.productUrl)}" target="_blank" rel="noreferrer">在东方行查看原商品 ↗</a>`
    : "";
  const classes = ["offer", almost ? "almost-expired" : ""].filter(Boolean).join(" ");
  return `<article class="${classes}">
    <div class="photo">${img}${badge}</div>
    <div class="offer-body">
      <p class="category">${esc(offer.displayCategory || offer.categoryZh || offer.category)}</p>
      <h3>${esc(offer.nameZh)}</h3>
      ${dutch}
      ${validity}
      ${pack}
      ${prep}
      ${priceRow}
      ${unit}
      <p class="advice">${esc(offer.advice || "")}</p>
      ${product}
    </div>
  </article>`;
}

function bindImageErrors(root) {
  root.querySelectorAll("img").forEach((img) => {
    img.addEventListener("error", () => { img.style.display = "none"; });
  });
}

function render(data, state, resultsOnly = false) {
  const stale = Date.now() - Date.parse(data.generatedAt) > 36 * 60 * 60 * 1000;
  const query = state.query.trim().toLowerCase();
  const filtered = sortOffers(
    (data.offers || []).filter((item) => {
      if (!matchesFilter(item, state.category)) return false;
      if (!query) return true;
      const haystack = `${item.nameZh} ${item.name} ${item.brand} ${item.displayCategory} ${item.category} ${item.promo || ""}`.toLowerCase();
      return haystack.includes(query);
    }),
    state.sortBy
  );

  const root = document.getElementById("root");
  if (resultsOnly) {
    root.querySelector("[data-role=result-count]").textContent = `全部优惠 · ${filtered.length} 项`;
    root.querySelector(".offer-grid").innerHTML = filtered.map(card).join("");
    bindImageErrors(root);
    return;
  }
  root.innerHTML = `<main class="page">
    <header class="hero">
      <a class="repo-link" href="https://github.com/cody1991/oriental-dirk-compare" target="_blank" rel="noreferrer" aria-label="在 GitHub 查看本项目仓库">GitHub 仓库 <span>↗</span></a>
      <div class="stamp">东方 / 本周</div>
      <div>
        <div class="hero-meta">
          <p class="kicker">${esc(data.store?.name ?? "Amazing Oriental")} · ${esc(data.store?.address ?? "")} · ${esc(data.store?.closedToday ? "今日休息" : `今日关店 ${data.store?.closesAt ?? "待确认"}`)}</p>
          <a class="official-link" href="${esc(data.sourceUrl)}" target="_blank" rel="noreferrer">官方优惠页 <span>↗</span></a>
          <a class="official-link" href="${esc(data.store?.url || data.store?.hoursSourceUrl || "")}" target="_blank" rel="noreferrer">门店营业时间 <span>↗</span></a>
        </div>
        <h1>本周，把<em>优惠</em>看全。</h1>
        <p class="subhead">当前惊奇东方行优惠的价格、折扣与商品图，一页看完。优惠来自全连锁官网，Almere 分店有没有货要到店才知道。</p>
        <p class="hours-note">${esc(data.store?.hoursNote || "")}</p>
      </div>
      <div class="update${stale ? " stale" : ""}"><b>${esc(data.offers.length)}</b><span>个优惠<br />${stale ? "数据等待更新" : "最近更新"}<br />${esc(dateFmt.format(new Date(data.generatedAt)))}</span></div>
    </header>
    <section class="catalogue" aria-labelledby="catalogue-title">
      <div class="catalogue-head">
        <div>
          <span data-role="result-count" aria-live="polite">全部优惠 · ${filtered.length} 项</span>
          <h2 id="catalogue-title">本周优惠。</h2>
          <p class="catalogue-summary">按折扣、单位价格或售价排序。${esc(data.validity?.weeklyZh || "")}。${esc(data.validity?.amazingZh || "")}。<span class="validity-nl">${esc([data.validity?.weeklyNl, data.validity?.amazingNl].filter(Boolean).join(" · "))}</span></p>
        </div>
        <div class="catalogue-controls">
          <div class="sort-control" aria-label="排序方式">
            <span>排序</span>
            <div class="sort-options">
              ${SORTS.map((option) => `<button type="button" data-sort="${esc(option.value)}" class="${option.value === state.sortBy ? "selected" : ""}" aria-pressed="${option.value === state.sortBy}">${esc(option.label)}</button>`).join("")}
            </div>
          </div>
          <input value="${esc(state.query)}" data-role="search" placeholder="搜索：烤鸭、云吞、方便面…" aria-label="搜索优惠" />
        </div>
      </div>
      <div class="filters">
        ${FILTERS.map((item) => `<button type="button" data-category="${esc(item.value)}" class="${item.value === state.category ? "selected" : ""}">${esc(item.label)}</button>`).join("")}
      </div>
      <div class="offer-grid">
        ${filtered.map(card).join("")}
      </div>
    </section>
    <footer>
      数据来自 <a href="${esc(data.sourceUrl)}" target="_blank" rel="noreferrer">Amazing Oriental 全连锁官网优惠页</a>；Almere 分店营业时间来自 <a href="${esc(data.store?.hoursSourceUrl || data.store?.url || "")}" target="_blank" rel="noreferrer">官方店页</a>。分店有没有货要到店才知道。
      没有划掉原价的商品只展示现价，不当折扣。官方只写「2 件 €x」「买 3 送 1」时按原文保留。图片与价格以门店实际标签为准。本页是刷新时的快照，通常每天更新。
      样式参考了 Cody 的 Dirk 看板，本页不是 Dirk 或东方行的官方站。
    </footer>
  </main>`;

  bindImageErrors(root);
  root.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      state.category = button.getAttribute("data-category");
      render(data, state);
    });
  });
  root.querySelectorAll("[data-sort]").forEach((button) => {
    button.addEventListener("click", () => {
      state.sortBy = button.getAttribute("data-sort");
      render(data, state);
    });
  });
  const search = root.querySelector("[data-role=search]");
  if (search) {
    // Keep the actual input node alive, including its native IME session and caret.
    let composing = false;
    const updateSearch = () => {
      state.query = search.value;
      render(data, state, true);
    };
    search.addEventListener("compositionstart", () => { composing = true; });
    search.addEventListener("compositionend", () => {
      composing = false;
      updateSearch();
    });
    search.addEventListener("input", (event) => {
      if (composing || event.isComposing) return;
      updateSearch();
    });
  }
}

fetch("./data/offers.json")
  .then((response) => {
    if (!response.ok) throw new Error("missing data");
    return response.json();
  })
  .then((data) => render(data, { category: "全部", query: "", sortBy: "discount" }))
  .catch(() => {
    document.getElementById("root").innerHTML = '<main class="loading">今天的数据还没有准备好。请稍后刷新。</main>';
  });
