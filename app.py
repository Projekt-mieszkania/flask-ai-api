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

        # Изображения — исключаем баннеры и иконки
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http") and "CatImg" not in src and "icon" not in src:
                images.append(src)
            if len(images) >= 5:
                break

        # Атрибуты — парсим списки или таблицы, если есть
        attributes = []
        for ul in soup.select("ul.product-attributes, ul.attributes, ul.characteristics"):
            for li in ul.select("li"):
                parts = li.get_text(strip=True).split(":")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    value = parts[1].strip()
                    attributes.append({
                        "name": name,
                        "options": [value],
                        "visible": True,
                        "variation": False
                    })

        # Альтернатива: таблица
        table = soup.select_one("table")
        if table:
            for row in table.select("tr"):
                cols = row.select("td")
                if len(cols) >= 2:
                    name = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    attributes.append({
                        "name": name,
                        "options": [value],
                        "visible": True,
                        "variation": False
                    })

        return jsonify({
            "title": title,
            "description": description,
            "seo": {
                "meta_title": title,
                "meta_description": description[:160],
                "keywords": [word.lower() for word in title.split() if len(word) > 3]
            },
            "images": images,
            "attributes": attributes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

