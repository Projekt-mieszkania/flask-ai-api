from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Конфигурация WooCommerce
WC_URL = "https://projekt-mieszkania.pl"
WC_KEY = "ck_f5c91a1d42a5dc898fe3fea084d464a29b9a2466"
WC_SECRET = "cs_2d80076cdfa0e571855e1965115387ec5946495b"

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"

# Получение всех глобальных атрибутов из WooCommerce
def get_wc_attributes():
    try:
        response = requests.get(
            f"{WC_URL}/wp-json/wc/v3/products/attributes",
            auth=(WC_KEY, WC_SECRET),
            timeout=10
        )
        data = response.json()
        return {item["name"]: item["slug"] for item in data}
    except Exception as e:
        return {}

def rewrite_description(text):
    payload = {
        "inputs": f"Przepisz ten opis produktu w sposób unikalny, naturalny i marketingowy:\n{text}"
    }

    try:
        response = requests.post(HUGGINGFACE_API_URL, json=payload, timeout=60)
        result = response.json()
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"]
        else:
            return text
    except Exception as e:
        return text

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        wc_slugs = get_wc_attributes()

        # Название
        title = "Bez nazwy"
        for selector in ['h1', 'h1.product-title', 'h1[itemprop=name]', 'meta[property="og:title"]']:
            tag = soup.select_one(selector)
            if tag:
                title = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        # Описание
        description = ""
        for selector in ['div.description', 'div.product-description', 'div[itemprop=description]', 'meta[name="description"]']:
            tag = soup.select_one(selector)
            if tag:
                description = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        if not description and title != "Bez nazwy":
            description = f"{title} to nowoczesny i funkcjonalny produkt idealny do każdego wnętrza. Charakteryzuje się wysoką jakością wykonania i atrakcyjnym designem."

        rewritten = rewrite_description(description)

        # Изображения
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http") and "CatImg" not in src and "icon" not in src:
                images.append(src)
            if len(images) >= 5:
                break

        # Атрибуты
        attributes = []
        param_header = soup.find(lambda tag: tag.name in ['h2', 'div'] and "Parametry produktu" in tag.get_text())
        if param_header:
            param_block = param_header.find_next()
            if param_block:
                lines = param_block.get_text(separator="\n").split("\n")
                i = 0
                while i < len(lines) - 1:
                    name = lines[i].strip().strip(":")
                    value = lines[i + 1].strip()
                    if name and value and len(name) < 60 and len(value) < 100:
                        attributes.append({
                            "name": name,
                            "slug": wc_slugs.get(name, ""),
                            "options": [value],
                            "visible": True,
                            "variation": False
                        })
                        i += 2
                    else:
                        i += 1

        return jsonify({
            "title": title,
            "description": rewritten,
            "seo": {
                "meta_title": title,
                "meta_description": rewritten[:160],
                "keywords": [word.lower() for word in title.split() if len(word) > 3]
            },
            "images": images,
            "attributes": attributes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
