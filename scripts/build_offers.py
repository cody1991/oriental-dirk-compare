#!/usr/bin/env python3
"""Parse Amazing Oriental aanbiedingen HTML into data/offers.json."""

from __future__ import annotations

import html as htmllib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HTML_CANDIDATES = [Path("/tmp/ao-fresh.html"), Path("/tmp/ao.html")]

SECTIONS = [
    ("weekly-specials", "Weekly Deals", "weekly", "本周特价", "2026-11-25", "2026-12-01"),
    ("amazingdeals", "Amazing Deals", "amazing", "Amazing Deals", "2026-11-18", "2026-12-08"),
    ("megadeals", "Mega Deals", "mega", "Mega Deals", "2026-11-18", "2026-12-08"),
    ("vis-en-vlees", "Vis en vlees", "meat", "鱼和肉", "2026-11-18", "2026-12-08"),
]

PACKAGE_ZH = {
    "per kilo": "每公斤",
    "per pak": "每包",
    "per fles": "每瓶",
    "per pot": "每罐",
    "per cup": "每杯",
    "per stuk": "每只",
    "per zak": "每袋",
    "per blik": "每罐",
    "per doos": "每箱",
    "per 500g": "每 500 g",
    "500g": "每 500 g",
}

# (brand or "", official name) -> Chinese name
NAME_ZH = {
    ("Dag Vers", "Eddo"): "芋头",
    ("Dag Vers", "Chayote"): "佛手瓜",
    ("Dag Vers", "Flespompoen"): "蒲瓜",
    ("Dag Vers", "Shimeji Brown"): "蟹味菇",
    ("Dag Vers", "Rambutan Vietnam (Air)"): "空运红毛丹",
    ("Dag Vers", "Mini Pak Choi"): "小白菜",
    ("Lee Kum Kee", "Zoete Sojasaus voor Dim Sum & Rijst"): "点心与米饭用甜酱油",
    ("Lee Kum Kee", "Chiu Chow Chilli Oil"): "潮州辣椒油",
    ("Lee Kum Kee", "Hot Chilli Soy Sauce"): "香辣酱油",
    ("Lee Kum Kee", "Rice Vinegar"): "米醋",
    ("Lee Kum Kee", "Saus voor Dumplings"): "饺子蘸酱",
    ("Lee Kum Kee", "Premium Paddenstoelen Kruidenpoeder"): "特级蘑菇调味粉",
    ("Lee Kum Kee", "Sichuan Spicy Noodle Sauce"): "四川担担面酱",
    ("Lee Kum Kee", "Red Braising Sauce"): "红烧酱",
    ("Lee Kum Kee", "Sichuan Style Hot & Spicy Stir Fry Sauce"): "四川香辣炒菜酱",
    ("Lee Kum Kee", "Alle Stir Fry Sauce"): "炒菜酱（全系列）",
    ("Chee Seng", "Pure Sesame Oil"): "纯芝麻油",
    ("Oke", "Handmade Egg Rolls"): "手工蛋卷",
    ("Oke", "Wife Cake"): "老婆饼",
    ("Oke", "Egg Yolk Puff Red Bean Paste"): "蛋黄红豆酥",
    ("Oke", "Macau Assorted Biscuits Gift"): "澳门什锦饼干礼盒",
    ("Oke", "Assorted Biscuits"): "什锦饼干",
    ("Oke", "Assorted Biscuits Macau"): "澳门什锦饼干",
    ("Oke", "Dual Layer Box Assorted Biscuits"): "双层什锦饼干礼盒",
    ("Gold Kili", "Natural Ginger Bag with Lemongrass"): "香茅姜茶",
    ("Gold Kili", "Instant Matcha Latte"): "即溶抹茶拿铁",
    ("Gold Kili", "Instant Ginger Latte with Honey"): "即溶蜂蜜姜汁拿铁",
    ("Gold Kili", "Instant Matcha Ginger Latte"): "即溶姜汁抹茶拿铁",
    ("Gold Kili", "Instant Ginger Tea Latte with Honey"): "即溶蜂蜜姜茶拿铁",
    ("Surasang", "Sliced Rice Cake"): "切片年糕",
    ("Surasang", "Rice Cake Stick"): "条状年糕",
    ("Kabuki", "Instant Ramen Soy Sauce Flavor"): "酱油味方便拉面",
    ("Kabuki", "Instant Kabuki Ramen Miso Smaak."): "味噌味方便拉面",
    ("Kabuki", "Instant Kabuki Ramen Tonkotsu Flavor"): "豚骨味方便拉面",
    ("Indomie", "Instant Noodles Mi Goreng"): "炒面（Mi Goreng）",
    ("Indomie", "Instant Noodles Chicken Flavour"): "鸡肉味方便面",
    ("Indomie", "Instant Cup Noodles Chicken Flavour"): "鸡肉味杯面",
    ("Indomie", "Instant Noodles Mi Goreng BBQ Chicken Flavour"): "烧烤鸡肉味炒面",
    ("Dynasty", "Jasmijnrijst"): "茉莉香米",
    ("White Tower", "Tomatenpuree"): "番茄酱",
    ("Ebi", "Vannamei PD Garnalen 26/30"): "去壳南美白虾 26/30",
    ("Seacon", "Vannamei Ongepelde Garnalen Zonder Kop 16/20"): "不去壳去头南美白虾 16/20",
    ("Lucky Duck", "Geroosterde Eend Zonder Kop"): "烤鸭（整只去头）",
    ("Oriental", "Bevroren Zwarte Kip"): "冷冻乌鸡",
    ("", "Rauwe Eendenpoten"): "生鸭掌",
    ("Oriental", "Kwartel"): "鹌鹑",
    ("", "Iberico Procureur (gesneden 1,5mm)"): "伊比利亚猪梅花肉（切片 1.5 mm）",
    ("", "Iberico Pork Belly Rindless"): "伊比利亚猪五花（去皮）",
    ("Chi Mei", "Fluffy Leek Chinese Pancake"): "葱油饼",
    ("Chi Mei", "Japanese Stir Fried Ginger Flavor Gyoza"): "日式炒姜味锅贴",
    ("Chi Mei", "Sesame Bun"): "芝麻包",
    ("Chi Mei", "Plant-Based Meat Bun Japanese Stir Fried Ginger Flavour"): "日式炒姜味素肉包",
    ("Delico", "Lo Mai Kai"): "糯米鸡",
    ("Delico", "Pork Sieuw Mai"): "猪肉烧卖",
    ("Delico", "Beef Sieuw Mai"): "牛肉烧卖",
    ("Delico", "Chicken Sieuw Mai"): "鸡肉烧卖",
    ("Do Do", "Cuttlefish Ball"): "墨鱼丸",
    ("Do Do", "Visballen"): "鱼丸",
    ("Do Do", "Fried Fish Ball"): "炸鱼丸",
    ("Do Do", "Tofu Fish Cake"): "豆腐鱼饼",
    ("CP", "Instant Shrimp Wonton Soup"): "即食虾云吞汤",
    ("CP", "Shrimp Wonton Soup with Choy Sum"): "菜心虾云吞汤",
    ("CP", "Instant Shrimp Wonton Soup With Noodles"): "虾云吞汤面",
    ("CP", "Whole Shrimp Wonton in Tom Yum Soup"): "冬阴功整只虾云吞",
    ("Meirun", "Pork Xiaolongbao"): "猪肉小笼包",
    ("Meirun", "Pork Dumplings with Shrimp"): "猪肉虾饺",
    ("Meirun", "Pork Dumplings with Cabbage"): "白菜猪肉饺子",
    ("Meirun", "Pork Dumplings with Mushroom"): "香菇猪肉饺子",
    ("Meirun", "Pork Dumplings with Chives"): "韭菜猪肉饺子",
    ("Koyuki", "Mochi Ice Matcha"): "抹茶麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Vanilla"): "香草麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Strawberry"): "草莓麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Coconut Flavor"): "椰子麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Yuzu Flavor"): "柚子麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Mango Flavor"): "芒果麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Black Sesame Flavor"): "黑芝麻麻薯冰淇淋",
    ("Koyuki", "Mochi Ice Pistachio Flavor"): "开心果麻薯冰淇淋",
    ("Altive", "Altive Monaka Dairy Free Red Bean Flavor"): "无乳红豆最中冰淇淋",
    ("CJ", "Altive Monaka Dairy Free Chestnut Flavor"): "无乳栗子最中冰淇淋",
    ("CJ", "Altive Monaka Dairy Free Matcha Flavor"): "无乳抹茶最中冰淇淋",
    ("CJ", "Altive Monaka Dairy Free Chocolate Flavor"): "无乳巧克力最中冰淇淋",
    ("Saongwon", "Vegetable Pancake"): "蔬菜饼",
    ("Saongwon", "Kimchi Pancake"): "泡菜饼",
    ("Chang Li Sheng", "Taiwanese Flaky Pancake"): "台湾手抓饼",
    ("Chang Li Sheng", "Meigan Pancake"): "梅干菜饼",
    ("Chang Li Sheng", "Fresh Beancurd Skins"): "鲜腐皮",
    ("SamYang", "Buldak Kimchi Dumpling"): "火鸡泡菜饺子",
    ("SamYang", "Hot Chicken Carbonara Ramen"): "火鸡奶油培根拉面",
    ("Shimadaya", "Frozen Ramen Noodles"): "冷冻拉面",
    ("Jongga", "Mat Kimchi"): "切片泡菜",
    ("Jongga", "Rice Cake (Sliced Type)"): "切片年糕",
    ("Jongga", "Rice Cake (Tubular Type)"): "条状年糕",
    ("Nissin", "Instant Noodles Spicy Seafood Flavour"): "香辣海鲜方便面",
    ("Bibigo", "Korean Style Udon Noodles K-BBQ Flavor"): "韩式烤肉味乌冬面",
    ("Bibigo", "Korean Style Udon Noodles Tteokbokki Chilli Flavor"): "辣炒年糕味乌冬面",
    ("Bibigo", "Gochujang Red Pepper Paste"): "韩式辣椒酱（Gochujang）",
    ("Bibigo", "Ssamjang Seasoned Soybean Paste"): "韩式包饭酱（Ssamjang）",
    ("Hakuro", "Hakuro Koshihikari Short Grain Japonica Rice"): "越光短粒米",
    ("Haday", "Wei Ji Xian Seasoning Sauce"): "味极鲜调味汁",
    ("Haday", "Superior Taste Oyster Sauce"): "特级蚝油",
    ("Haday", "0 Additives Hot Soybean Sauce"): "零添加香辣黄豆酱",
    ("Hao Ren Jia", "Seasoning for Beef in Sour Soup"): "酸汤肥牛调味料",
    ("Hao Ren Jia", "Seasoning for Fish with Sour Cabbage"): "酸菜鱼调味料",
    ("Hao Ren Jia", "Spicy Hot Pot Soup Base with Hawthorn"): "山楂麻辣火锅底料",
    ("Hao Ren Jia", "Spicy Hot Pot Soup Base"): "麻辣火锅底料",
    ("Golden Diamond", "Tonic Yam & Medeberry Soepkruiden"): "淮山枸杞炖汤料",
    ("Golden Diamond", "Shashen Yuzhu Herbal Soup Stock"): "沙参玉竹炖汤料",
    ("Golden Diamond", "Voedzame Groenten. & Paddenstoelen Soepbouillon"): "营养蔬菜蘑菇汤料",
    ("Golden Diamond", "Zi Yin Run Fei Soepkruiden"): "滋阴润肺炖汤料",
    ("Golden Diamond", "Pak Kee Tangshen Soepkruiden"): "北芪党参炖汤料",
    ("Golden Diamond", "Yang Yan Soup Stock"): "养颜炖汤料",
    ("Golden Diamond", "Cordyceps Tonic Soepkruiden"): "虫草花炖汤料",
    ("CJ", "Rode Peperpasta (Gochujang)"): "韩式辣椒酱（Gochujang）",
    ("CJ", "Bibigo Korean Hot Pepper Paste"): "Bibigo 韩式辣椒酱",
    ("Otafuku", "Okonomiyaki Takoyaki Flour"): "大阪烧／章鱼烧粉",
    ("Otafuku", "Vegan Okonomi Sauce"): "素食大阪烧酱",
    ("Otafuku", "Okonomi Spicy Sauce"): "香辣大阪烧酱",
    ("Otafuku", "Tenkasu Tempura Crisps"): "天妇罗碎",
    ("Otafuku", "Dried Red Pickled Ginger"): "红姜丝",
    ("Otafuku", "Senmai Vinegar"): "千枚醋",
    ("My Chef", "Sweet Chilli Sauce"): "甜辣酱",
    ("Crying Thaiger", "Sriracha Chilli Sauce"): "是拉差辣椒酱",
    ("Suree", "Coconut Milk"): "椰浆",
    ("O'Food", "Tteokbokki Sauce"): "炒年糕酱",
    ("O'Food", "Soup Base for Spicy Army Stew Budaejjigae"): "部队锅汤底",
    ("O'Food", "Soup Base for Spicy Tofu Stew Sundubujjigae"): "嫩豆腐锅汤底",
    ("O'Food", "Soup Base with Soybean Paste Doenjangjjigae"): "大酱汤汤底",
    ("O'Food", "Luncheon Meat"): "午餐肉",
    ("O'Food", "Gochujang Red Pepper Paste"): "韩式辣椒酱（Gochujang）",
    ("O'Food", "Sunchang Ssamjang Gekruide Bonenpasta"): "淳昌包饭酱",
    ("O'Food", "Ssamjang Mixed Soy Bean Paste"): "包饭酱",
    ("Chung Jung One", "Ssamjang Seasoned Korean Soybean Paste"): "韩式包饭酱",
    ("Chung Jung One", "Sliced Seaweed"): "海苔片",
    ("Chung Jung One", "Seasoned Seaweed Snack with Olive Oil"): "橄榄油调味海苔",
    ("Chung Jung One", "Traditional Laver with Olive Oil"): "橄榄油传统海苔",
    ("Wayong", "Pika Curacao"): "库拉索 Pika 辣椒酱",
    ("Wayong", "Sambal Triple Hot"): "三倍辣参峇酱",
    ("Sunlee/Div. Merken", "Sweet Corn on the Cob"): "甜玉米棒",
    ("Yummy House", "Bird Eye Chili Sauce"): "小米椒辣椒酱",
    ("Tian Peng", "Wasabi Powder"): "芥末粉",
    ("Sunlee", "Rambutan With Pineapple In Syrup"): "糖水红毛丹菠萝",
    ("Hot Kid", "QQ Gummy Candy 3 Flavour"): "QQ 软糖（三种口味）",
    ("Hot Kid", "QQ Gummy Candy (Lychee / Peach / Pineapple / Apple Flavour)"): "QQ 软糖（荔枝／桃／菠萝／苹果）",
    ("Cozzo", "Konnyaku Jelly Lychee Flavor"): "荔枝魔芋果冻",
    ("Cozzo", "Konnyaku Jelly Mango Flavor"): "芒果魔芋果冻",
    ("Cozzo", "Konnyaku Jelly Blueberry Flavour"): "蓝莓魔芋果冻",
    ("Cozzo", "Pudding Mango Flavor"): "芒果布丁",
    ("Cozzo", "Pudding Lychee Flavor"): "荔枝布丁",
    ("Cozzo", "Pudding Peach Flavor"): "水蜜桃布丁",
    ("Heng Kang", "Sunflower Seed Coconut Flavour"): "椰子味瓜子",
    ("Bestore", "Roasted Broad Beans with Spicy Flavour"): "香辣兰花豆",
    ("Kameda", "Shoyu Honey Rice Cracker"): "酱油蜂蜜米果",
    ("Kameda", "Mini Honey Rice Cracker"): "迷你蜂蜜米果",
    ("Yopokki", "Yoppokki Snack Hot & Spicy Flavor"): "香辣炒年糕零食",
    ("Yopokki", "Sweet & Spicy Rapokki"): "甜辣拉炒年糕",
    ("Yopokki", "Kimchi Rapokki"): "泡菜拉炒年糕",
    ("If", "Coconut Water 100%"): "100% 椰子水",
    ("Green Dot Dot", "Matcha Wellness Tea Capsule"): "抹茶养生茶胶囊",
    ("Green Dot Dot", "Pu'er with Chrysanthemum Wellness Tea Capsule"): "菊花普洱茶胶囊",
    ("Green Dot Dot", "Pu'er with Tangerine Peel Wellness Tea Capsule"): "陈皮普洱茶胶囊",
    ("Kamcha", "HK Style Yuan Yang (Coffee & Tea) Capsule"): "港式鸳鸯胶囊",
    ("Kamcha", "HK Style Ceylon Tea Capsule"): "港式锡兰茶胶囊",
    ("Ichinoya", "Hitogokochi Kimoto Junmai Ginjo Sake"): "人心地 生酛 纯米吟酿清酒",
    ("Gekkeikan", "Traditionele Sake (Japan)"): "传统清酒",
    ("Gekkeikan", "Traditional Sake (Japan)"): "传统清酒",
    ("Gekkeikan", "Nigori Sake"): "浊酒",
    ("Kook Soon Dang", "Makgeolli Rice Wine"): "米酒",
    ("Kook Soon Dang", "Makgeolli Rice Wine Banana Flavor"): "香蕉味米酒",
    ("Kook Soon Dang", "Makgeolli Rice Wine White Grape Flavor"): "白葡萄味米酒",
    ("Kook Soon Dang", "Makgeolli Rice Wine Peach Flavor"): "桃味米酒",
    ("Acecook", "Alle Hao Hao Instant Noodles"): "Hao Hao 方便面（全系列）",
    ("Jinjili", "Sesame Ball / Glutinous Rice Ball Egg Custard Filling"): "芝麻球／蛋奶黄糯米球（全系列）",
    ("Visafdeling", "Zalmbuik"): "三文鱼腹",
    ("Visafdeling", "Roodbaars"): "红鱼",
    ("Visafdeling", "Sliptong"): "龙利鱼（Sliptong）",
    ("Vleesafdeling", "Klapstuk"): "牛胸肉（Klapstuk）",
    ("Vleesafdeling", "Kippendijfilet zonder Vel"): "去皮鸡腿肉",
    ("Vleesafdeling", "Verse Varkensprocureur"): "新鲜猪梅花肉",
    ("Vleesafdeling", "Geroosterd varkensvlees"): "烤猪肉",
    ("Vleesafdeling", "Geroosterd Buikspek"): "烤五花",
    ("Vleesafdeling", "Gegrilde Spareribs"): "烤排骨",
}

# Short, factual prep notes only when clearly ready-to-eat or just heat.
PREP = {
    "Lucky Duck 烤鸭（整只去头）": "现成可吃",
    "烤猪肉": "现成可吃",
    "烤五花": "现成可吃",
    "烤排骨": "现成可吃",
    "手工蛋卷": "开袋即食",
    "老婆饼": "开袋即食",
    "蛋黄红豆酥": "开袋即食",
    "糯米鸡": "蒸或微波",
    "猪肉烧卖": "蒸",
    "牛肉烧卖": "蒸",
    "鸡肉烧卖": "蒸",
    "芝麻包": "蒸或微波",
    "日式炒姜味锅贴": "煎或蒸",
    "葱油饼": "煎或加热",
    "日式炒姜味素肉包": "蒸或微波",
    "猪肉小笼包": "蒸",
    "猪肉虾饺": "煮或蒸",
    "白菜猪肉饺子": "煮或蒸",
    "香菇猪肉饺子": "煮或蒸",
    "韭菜猪肉饺子": "煮或蒸",
    "火鸡泡菜饺子": "煮或煎，会辣",
    "即食虾云吞汤": "加热即食",
    "菜心虾云吞汤": "加热即食",
    "虾云吞汤面": "加热即食",
    "冬阴功整只虾云吞": "加热即食",
    "鸡肉味杯面": "冲泡即可",
    "鸡肉味方便面": "煮或冲泡",
    "炒面（Mi Goreng）": "煮或冲泡",
    "烧烤鸡肉味炒面": "煮或冲泡",
    "酱油味方便拉面": "煮或冲泡",
    "味噌味方便拉面": "煮或冲泡",
    "豚骨味方便拉面": "煮或冲泡",
    "香辣海鲜方便面": "煮或冲泡",
    "火鸡奶油培根拉面": "煮或冲泡，会辣",
    "Hao Hao 方便面（全系列）": "煮或冲泡",
}

URL_PACKAGE = {
    "https://amazingoriental.com/product/surasang-rijstcake-gesneden-907g/": "907 g",
    "https://amazingoriental.com/product/surasang-gesneden-rijstcake-650g/": "650 g",
}


def clean(text: str | None) -> str | None:
    if not text:
        return None
    text = htmllib.unescape(re.sub(r"<br\s*/?>", " ", text, flags=re.I))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip().replace("\xa0", " ").replace("€", "").strip()
    if not text:
        return None
    if re.search(r"\d+\.\d{3}", text) and "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def section_html(raw: str, sec_id: str) -> str:
    match = re.search(rf'id="{re.escape(sec_id)}"', raw)
    if not match:
        return ""
    start = match.start()
    end = len(raw)
    for other, *_ in SECTIONS:
        if other == sec_id:
            continue
        found = re.search(rf'id="{re.escape(other)}"', raw)
        if found and found.start() > start:
            end = min(end, found.start())
    return raw[start:end]


def package_zh(package: str, url: str) -> str:
    extra = URL_PACKAGE.get(url)
    key = package.lower()
    zh = PACKAGE_ZH.get(key, package)
    if extra and extra not in zh:
        zh = f"{zh} {extra}" if zh else extra
    return zh


def unit_price(sale: float | None, package: str) -> float | None:
    if sale is None:
        return None
    key = package.lower()
    if key in {"per kilo"}:
        return round(sale, 2)
    if key in {"per 500g", "500g"}:
        return round(sale * 2, 2)
    return None


def discount_percent(sale: float | None, original: float | None) -> int | None:
    if sale is None or original is None or original <= 0 or sale >= original:
        return None
    return int(round((original - sale) / original * 100))


def advice_for(item: dict) -> str:
    parts: list[str] = []
    promo = item.get("promo")
    sale, original = item.get("sale"), item.get("original")
    if promo and sale is None:
        parts.append(f"官网活动为「{promo}」。")
        if original is not None:
            parts.append(f"页上单件标价 €{original:.2f}。".replace(".", ","))
        parts.append("没有单独现价，不把自行换算的价格写成折扣价。")
    elif original is None:
        parts.append("页面没有划掉原价，不当折扣。")
    elif sale is not None:
        off = original - sale
        pct = item.get("discountPercent")
        if pct:
            parts.append(f"现价比标出的原价少 €{off:.2f}，折扣 {pct}%。".replace(".", ","))
        else:
            parts.append(f"现价 €{sale:.2f}，原价 €{original:.2f}。".replace(".", ","))
    prep = item.get("prep")
    if prep:
        parts.append(prep + "。")
    return "".join(parts)


def parse_items(raw: str) -> list[dict]:
    parsed = []
    for sec_id, sec_name, sec_key, sec_zh, valid_from, valid_to in SECTIONS:
        block = section_html(raw, sec_id)
        date_m = re.search(r'class="se-date">([^<]+)', block)
        validity_nl = clean(date_m.group(1)) if date_m else None
        if sec_key == "weekly":
            validity_zh = "有效期为11月25日星期三至12月1日星期二"
        else:
            validity_zh = "有效期为11月18日至12月8日"
        for ib in re.findall(r'<div class="item">(.*?)</a></div>', block, flags=re.S):
            href = re.search(r'href="(https://amazingoriental.com/product/[^"]+)"', ib)
            if not href:
                continue
            url = href.group(1)
            webp = re.search(r'data-bg="(https://amazingoriental.com/wp-content/uploads/[^"]+\.webp)"', ib)
            png = re.search(r'data-bg="(https://amazingoriental.com/wp-content/uploads/[^"]+\.png)"', ib)
            brand = clean(re.search(r'<span class="brand">(.*?)</span>', ib).group(1) if re.search(r'<span class="brand">(.*?)</span>', ib) else "")
            title = re.search(r"<h4>(.*?)</h4>", ib)
            orig_m = re.search(r'original-price[^"]*">\s*([^<]*)', ib)
            sale_m = re.search(r'new-price">\s*([^<]+)', ib)
            label = clean(re.search(r'<span class="label">([^<]*)</span>', ib).group(1) if re.search(r'<span class="label">([^<]*)</span>', ib) else "") or ""
            promo = clean(re.search(r'<span class="promo">([^<]*)</span>', ib).group(1) if re.search(r'<span class="promo">(.*?)</span>', ib) else "")
            # Promo badges like "Amazing Deals" are section labels, not multi-buy deals
            if promo in {None, "", "Amazing Deals", "Mega Deals", "Weekly Deals", "Vis en vlees"} or (
                promo and promo.startswith("Weekly ")
            ):
                promo = None
            orig_raw = orig_m.group(1).strip() if orig_m else ""
            name = clean(title.group(1) if title else "") or ""
            parsed.append({
                "category": sec_name,
                "categoryKey": sec_key,
                "categoryZh": sec_zh,
                "validFrom": valid_from,
                "validTo": valid_to,
                "validityNl": validity_nl,
                "validityZh": validity_zh,
                "name": name,
                "brand": brand or "",
                "sale": parse_price(sale_m.group(1) if sale_m else None),
                "original": parse_price(orig_raw) if orig_raw else None,
                "package": label,
                "promo": promo,
                "imageUrl": (webp.group(1) if webp else None) or (png.group(1) if png else None),
                "productUrl": url,
            })
    return parsed


def merge_unique(items: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    order: list[str] = []
    for item in items:
        url = item["productUrl"]
        if url not in by_url:
            rec = dict(item)
            rec["categories"] = [item["category"]]
            rec["categoryKeys"] = [item["categoryKey"]]
            rec["categoriesZh"] = [item["categoryZh"]]
            by_url[url] = rec
            order.append(url)
        else:
            rec = by_url[url]
            if item["category"] not in rec["categories"]:
                rec["categories"].append(item["category"])
                rec["categoryKeys"].append(item["categoryKey"])
                rec["categoriesZh"].append(item["categoryZh"])
    offers = []
    missing = []
    for url in order:
        rec = by_url[url]
        brand, name = rec["brand"], rec["name"]
        name_zh = NAME_ZH.get((brand, name))
        if not name_zh:
            missing.append((brand, name, url))
            name_zh = name  # fail loudly later
        rec["nameZh"] = name_zh
        rec["packageZh"] = package_zh(rec["package"], url)
        rec["unitPrice"] = unit_price(rec["sale"], rec["package"])
        rec["discountPercent"] = discount_percent(rec["sale"], rec["original"])
        rec["prep"] = PREP.get(name_zh)
        rec["advice"] = advice_for(rec)
        rec["displayCategory"] = " · ".join(rec["categoriesZh"])
        offers.append(rec)
    if missing:
        raise SystemExit("Missing translations:\n" + "\n".join(f"{b!r} | {n!r} | {u}" for b, n, u in missing))
    return offers


def main() -> None:
    html_path = next((p for p in HTML_CANDIDATES if p.exists()), None)
    if not html_path:
        raise SystemExit("No AO HTML found. Download https://amazingoriental.com/aanbiedingen/ first.")
    raw = html_path.read_text(errors="replace")
    offers = merge_unique(parse_items(raw))
    now = datetime.now(ZoneInfo("Europe/Amsterdam")).isoformat(timespec="seconds")
    data = {
        "generatedAt": now,
        "sourceUrl": "https://amazingoriental.com/aanbiedingen/",
        "store": {
            "name": "Amazing Oriental Almere",
            "address": "Metropolestraat 64",
            "url": "https://amazingoriental.com/aanbiedingen/",
            "hoursNote": "开门时间以门店当日为准。此前记录：周四 09:00–21:00。",
        },
        "validity": {
            "weeklyNl": "Geldig van 25 november t/m 1 december",
            "weeklyZh": "Weekly Deals 有效期为11月25日星期三至12月1日星期二",
            "amazingNl": "Geldig van 18/11/2026 t/m 08/12/2026",
            "amazingZh": "Amazing Deals、Mega Deals 与鱼和肉有效期为11月18日至12月8日",
        },
        "note": "优惠来自全连锁官网，Almere 分店有没有货要到店才知道。",
        "offers": offers,
    }
    out = ROOT / "data" / "offers.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    cats = Counter(tuple(o["categories"]) for o in offers)
    print(f"wrote {out} ({len(offers)} unique offers) from {html_path}")
    print("category combos:", dict(cats))
    print("with original", sum(1 for o in offers if o["original"] is not None))
    print("no original", sum(1 for o in offers if o["original"] is None))
    print("promo only", sum(1 for o in offers if o["sale"] is None))


if __name__ == "__main__":
    main()
