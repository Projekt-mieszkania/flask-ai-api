from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Название товара
        title = "Bez nazwy"
        for selector in ['h1', 'h1.product-title', 'h1[itemprop=name]', 'meta[property="og:title"]']:
            tag = soup.select_one(selector)
            if tag:
                title = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        # Попытка найти описание
        description = ""
        for selector in ['div.description', 'div.product-description', 'div[itemprop=description]', 'meta[name="description"]']:
            tag = soup.select_one(selector)
            if tag:
                description = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        # Если описания нет — подставим шаблон
        if not description and title != "Bez nazwy":
            description = f"{title} to nowoczesny i funkcjonalny produkt idealny do każdego wnętrza. Charakteryzuje się wysoką jakością wykonania i atrakcyjnym designem."

        # Картинки
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http"):
                images.append(src)
            if len(images) >= 3:
                break

        return jsonify({
            "title": title,
            "description": description,
            "seo": {
                "meta_title": title,
                "meta_description": description[:160],
                "keywords": [word.lower() for word in title.split() if len(word) > 3]
            },
            "images": images,
            "attributes": []
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
