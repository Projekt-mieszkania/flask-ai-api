from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from woocommerce import API

app = Flask(__name__)

# Подключение к WooCommerce
wcapi = API(
    url="https://projekt-mieszkania.pl",
    consumer_key="ck_f5c91a1d42a5dc898fe3fea084d464a29b9a2466",       # ← замените на ваш
    consumer_secret="cs_2d80076cdfa0e571855e1965115387ec5946495b",  # ← замените на ваш
    version="wc/v3"
)

# Проверка "мусорного" текста
def is_garbage(text):
    return (
        "var" in text or "=" in text or ";" in text or
        "{" in text or "}" in text or len(text) > 100 or
        not any(c.isalnum() for c in text)
    )

# Очистка текста
def clean_text(text):
    return text.replace("\n", " ").replace("\r", "").strip()

# Проверка и добавление атрибута в WooCommerce
def ensure_attribute_exists(name, slug):
    try:
        existing = wcapi.get("products/attributes").json()
        existing_names = [attr["name"].lower() for attr in existing]
        if name.lower() not in existing_names:
            wcapi.post("products/attributes", {
                "name": name,
                "slug": slug,
                "type": "select",
                "has_archives": True
            })
    except Exception as e:
        print(f"⚠️ Ошибка добавления атрибута '{name}': {e}")

# Обработка атрибутов
def clean_and_split_attributes(raw_attributes):
    seen = set()
    final_attrs = []
    blacklist = ['dodaj do koszyka', 'zapytaj o cenę', 'darmowa dostawa', 'facebook']

    for attr in raw_attributes:
        name = clean_text(attr["name"])
        value = clean_text(attr["options"][0])
        slug = name.lower().replace(" ", "-")

        if any(bad in value.lower() for bad in blacklist):
            continue

        lines = value.splitlines()
        for line in lines:
            if ":" in line:
                key, val = map(str.strip, line.split(":", 1))
                key = key.capitalize()
                val = val.strip()
                pair = (key.lower(), val.lower())
                if pair not in seen and not is_garbage(key) and not is_garbage(val):
                    seen.add(pair)
                    ensure_attribute_exists(key, key.lower().replace(" ", "-"))
                    final_attrs.append({
                        "name": key,
                        "options": [val],
                        "slug": "",
                        "visible": True,
                        "variation": False
                    })
        if ":" not in value:
            key = name.capitalize()
            val = value
            pair = (key.lower(), val.lower())
            if pair not in seen and not is_garbage(key) and not is_garbage(val):
                seen.add(pair)
                ensure_attribute_exists(key, key.lower().replace(" ", "-"))
                final_attrs.append({
                    "name": key,
                    "options": [val],
                    "slug": "",
                    "visible": True,
                    "variation": False
                })

    return final_attrs

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Заголовок
        title = soup.find("h1")
        title = title.get_text(strip=True) if title else "Bez nazwy"

        # Описание
        desc_tag = soup.find("div", class_="product-description") or soup.find("div", class_="description")
        description = desc_tag.get_text(strip=True) if desc_tag else f"{title} to nowoczesny produkt."

        # Изображения
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

        # Сырые атрибуты
        raw_attributes = []
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

        attributes = clean_and_split_attributes(raw_attributes)

        return jsonify({
            "title": title,
            "description": description,
            "seo": {
                "meta_title": title,
                "meta_description": description[:160],
                "keywords": [w.lower() for w in title.split() if len(w) > 3]
            },
            "images": images,
            "attributes": attributes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
