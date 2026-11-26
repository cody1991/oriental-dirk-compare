const euro = new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR" });
const dateFmt = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Europe/Amsterdam",
  dateStyle: "medium",
  timeStyle: "short"
});

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

function card(item) {
  const img = item.imageUrl
    ? `<img src="${esc(item.imageUrl)}" alt="${esc(item.nameZh)}" loading="lazy" decoding="async" />`
    : "";
  const badge = item.badge ? `<span>${esc(item.badge)}</span>` : "";
  const dutch = item.name ? `<p class="original-name">${esc(item.name)}</p>` : "";
  const pack = item.package ? `<p class="pack">${esc(item.package)}</p>` : "";
  const prep = item.prep ? `<p class="pack">${esc(item.prep)}</p>` : "";
  const original = item.original != null ? `<s>${price(item.original)}</s>` : "";
  const discount = item.original != null && item.discountPercent
    ? `<i>−${esc(item.discountPercent)}%</i>`
    : "";
  const unit = item.unitPrice != null ? `<span class="unit-price">${price(item.unitPrice)}/kg</span>` : "";
  const note = item.noteUrl
    ? `<a class="pick-link" href="${esc(item.noteUrl)}" target="_blank" rel="noreferrer">${esc(item.noteLabel || "相关商品 ↗")}</a>`
    : "";
  const linkLabel = item.store === "dirk" ? "在 Dirk 查看原商品 ↗" : "在东方行查看原商品 ↗";
  const product = item.productUrl
    ? `<a class="product-link" href="${esc(item.productUrl)}" target="_blank" rel="noreferrer">${linkLabel}</a>`
    : "";

  return `<article class="offer">
    <div class="photo">${img}${badge}</div>
    <div class="offer-body">
      <p class="category">${esc(item.category || "")}</p>
      <h3>${esc(item.nameZh)}</h3>
      ${dutch}
      ${pack}
      ${prep}
      <div class="price"><b>${price(item.sale)}</b>${original}${discount}</div>
      ${unit}
      <p class="advice">${esc(item.advice || "")}</p>
      ${note}${product}
    </div>
  </article>`;
}

function section(block) {
  const aside = block.aside
    ? `<p class="aside">${esc(block.aside)}${block.asideUrl ? ` <a href="${esc(block.asideUrl)}" target="_blank" rel="noreferrer">在 Dirk 查看 ↗</a>` : ""}</p>`
    : "";
  return `<section class="catalogue" aria-labelledby="${esc(block.id)}-title">
    <div class="catalogue-head">
      <div>
        <span>${esc(block.kicker)}</span>
        <h2 id="${esc(block.id)}-title">${esc(block.heading)}</h2>
        <p class="catalogue-summary">${esc(block.summary)}</p>
      </div>
    </div>
    <div class="offer-grid">
      ${(block.items || []).map(card).join("")}
    </div>
    ${aside}
  </section>`;
}

function render(data) {
  const dirkLocal = dateFmt.format(new Date(data.dirkGeneratedAt));
  const aoLocal = dateFmt.format(new Date(data.aoFetchedAt));
  const root = document.getElementById("root");
  root.innerHTML = `<main class="page">
    <header class="hero">
      <a class="repo-link" href="${esc(data.links.repo)}" target="_blank" rel="noreferrer" aria-label="在 GitHub 查看本项目仓库">GitHub 仓库 <span>↗</span></a>
      <div class="stamp">对照 / 本周</div>
      <div>
        <div class="hero-meta">
          <p class="kicker">个人购物对照 · 非官方页面</p>
          <a class="official-link" href="${esc(data.links.aoOffers)}" target="_blank" rel="noreferrer">东方行优惠页 <span>↗</span></a>
          <a class="official-link" href="${esc(data.links.dirkDashboard)}" target="_blank" rel="noreferrer">Dirk 优惠看板 <span>↗</span></a>
          <a class="official-link" href="${esc(data.links.dirkStore)}" target="_blank" rel="noreferrer">Dirk Almere 店页 <span>↗</span></a>
        </div>
        <h1>本周，<em>对照</em>着买。</h1>
        <p class="subhead">惊奇东方行（Amazing Oriental Almere）和本周 Dirk Almere 优惠的对照，给 Cody 自己用。不是两家店的官方站。</p>
      </div>
      <div class="update"><b>本周</b><span>东方行查阅<br />${esc(aoLocal)}<br />Dirk 数据 ${esc(dirkLocal)}</span></div>
    </header>
    <section class="verdict">
      <p class="kicker">本周结论</p>
      <p>在东方行，优先看肉柜现成的烤五花、烤猪肉或烤排骨，以及打折的 Lucky Duck 烤鸭；再带糯米鸡、烧卖或虾云吞这类加热就能吃的冷冻货。方便面和寿司这周交给 Dirk 更合适：YumYum 五包 €1,39（售完即止），Sushi4you Satoru 寿司 400 g €4,99。</p>
      <p class="notice">东方行优惠来自全连锁官网，Almere 店有没有货，要到店才知道。本页按本周对照来写，不是“现在赶去”的指引。此前记录：周四两家均为 21:00 关门，以后出门前请再看各店当日营业时间。</p>
    </section>
    ${data.sections.map(section).join("")}
    <footer>
      ${esc(data.validity.aoWeeklyZh)}。${esc(data.validity.aoAmazingZh)}。其中烤五花、烤猪肉、烤排骨没有划掉原价，不当折扣。${esc(data.validity.dirkZh)}。
      东方行数据来自 <a href="${esc(data.links.aoOffers)}" target="_blank" rel="noreferrer">Amazing Oriental 优惠页</a>，于 ${esc(aoLocal)}（欧洲/阿姆斯特丹）查阅。
      Dirk 数据来自 <a href="${esc(data.links.dirkDashboard)}" target="_blank" rel="noreferrer">Dirk 优惠看板</a> 快照（generatedAt ${esc(data.dirkGeneratedAt)}，合本地 ${esc(dirkLocal)}）。
      门店页：<a href="${esc(data.links.dirkStore)}" target="_blank" rel="noreferrer">Dirk Almere Schipperplein</a>。
      图片与价格以门店实际标签为准。
    </footer>
  </main>`;
  root.querySelectorAll("img").forEach((img) => {
    img.addEventListener("error", () => { img.style.display = "none"; });
  });
}

fetch("./data/compare.json")
  .then((response) => {
    if (!response.ok) throw new Error("missing data");
    return response.json();
  })
  .then(render)
  .catch(() => {
    document.getElementById("root").innerHTML = '<main class="loading">对照数据没有加载成功。请稍后刷新。</main>';
  });
