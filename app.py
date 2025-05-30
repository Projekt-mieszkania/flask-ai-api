from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

HF_API_URL = "https://Apalkova-product-rewriter.hf.space/run/predict"

def rewrite_description(text):
    try:
        if not text or len(text.strip()) < 50:
            return f"{text.strip()} - to doskonały wybór dla każdego wnętrza. Sprawdź ofertę!"
        res = requests.post(HF_API_URL, json={"data": [text]}, timeout=20)
        response = res.json()
        return response["data"][0].strip()
    except Exception as e:
        print(f"[AI-ERROR]: {e}")
        return f"{text.strip()} - to doskonały wybór dla każdego wnętrza. Sprawdź ofertę!"

def is_garbage(text):
    garbage_signals = [
        "cookie", "facebook", "napisz", "projekt", "@", "mailto",
        "dodaj do koszyka", "zobacz produkt", "zł", "promocja", "produkt"
    ]
    return (
        any(x in text.lower() for x in garbage_signals)
        or any(c in text for c in ["=", "{", "}", ";"])
        or len(text) > 150
        or not any(c.isalnum() for c in text)
    )

def clean_text(text):
    return text.replace("\n", " ").replace("\r", "").strip()

def normalize_unit_name(name):
    mapping = {
        "cmwysokość": "Wysokość",
        "cmgłębokość": "Głębokość",
        "cm": ""
    }
    name = name.lower().strip()
    for k, v in mapping.items():
        if k in name:
            return v
    return name.capitalize()

def extract_clean_name_value(name, value):
    match = re.search(r"(\d{2,4})\s*cm(\s*)?([a-ząćęłńóśźż]+)", name.lower())
    if match:
        val = f"{match.group(1)} cm"
        label = match.group(3).capitalize()
        return label, val
    label = normalize_unit_name(name)
    return label, value.strip()

def extract_dimensions_from_value(value):
    found = re.findall(r"([A-ZŁŚĆŻŹa-złśąćęńóźż]+):\s*(\d+\s*cm)", value)
    return [(k.capitalize(), v) for k, v in found] if found else []

def clean_and_split_attributes(raw_attributes):
    seen = {}

    for attr in raw_attributes:
        name_raw = clean_text(attr.get("name", ""))
        value_raw = clean_text(attr.get("options", [""])[0])

        # Обработка строки вида "Szerokość: 40 cmwysokość:54 cmgłębokość:41 cm"
        segments = re.findall(r"([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ\s]+):\s*([\d.,]+\s*(?:cm|mm|kg|g)?)", value_raw)
        if segments and len(segments) > 1:
            for name, val in segments:
                name = clean_text(name)
                val = clean_text(val)
                key = name.lower()
                if key in seen:
                    if val not in seen[key]["options"]:
                        seen[key]["options"].append(val)
                else:
                    seen[key] = {
                        "name": name,
                        "options": [val],
                        "slug": "",
                        "visible": True,
                        "variation": False
                    }
            continue

        # Пропуск мусора
        if is_garbage(name_raw) or is_garbage(value_raw):
            continue

        # Обычная пара
        name, value = extract_clean_name_value(name_raw, value_raw)
        key = name.lower()
        if key in seen:
            if value not in seen[key]["options"]:
                seen[key]["options"].append(value)
        else:
            seen[key] = {
                "name": name,
                "options": [value],
                "slug": "",
                "visible": True,
                "variation": False
            }

    return list(seen.values())

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "Bez nazwy"

        desc_tag = soup.find("div", class_="product-description") or soup.find("div", class_="description")
        description = desc_tag.get_text(strip=True) if desc_tag else f"{title} to nowoczesny produkt."
        rewritten = rewrite_description(description)

        price = None
        cat = None
        price_tag = soup.find(text=re.compile(r"\d+[,\.]\d+\s*zł"))
        if price_tag:
            match = re.search(r"(\d+[\.,]?\d*)", price_tag)
            if match:
                price = match.group(1).replace(",", ".")

        cat_tag = soup.find("span", class_="posted_in") or soup.find("span", class_="product-category")
        if cat_tag:
            cat = cat_tag.get_text(strip=True)

        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if (
                src.startswith("http")
                and not any(x in src.lower() for x in ["logo", "icon", "facebook", "svg"])
                and any(src.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])
            ):
                images.append(src)
            if len(images) >= 5:
                break

        raw_attributes = []

        # 1. Общие текстовые блоки
        for tag in soup.find_all(["li", "div", "p", "span"]):
            text = tag.get_text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                raw_attributes.append({
                    "name": parts[0],
                    "options": [parts[1]],
                    "slug": "",
                    "visible": True,
                    "variation": False
                })

        # 2. Поиск таблиц (например, DANE TECHNICZNE)
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) == 2:
                    name = clean_text(cells[0].get_text())
                    value = clean_text(cells[1].get_text())
                    raw_attributes.append({
                        "name": name,
                        "options": [value],
                        "slug": "",
                        "visible": True,
                        "variation": False
                    })

        attributes = clean_and_split_attributes(raw_attributes)

        return jsonify({
            "title": title,
            "description": rewritten,
            "price": price,
            "category": cat,
            "seo": {
                "meta_title": title,
                "meta_description": rewritten[:160],
                "keywords": [w.lower() for w in title.split() if len(w) > 3]
            },
            "images": images,
            "attributes": attributes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
