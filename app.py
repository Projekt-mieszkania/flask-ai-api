from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Название товара
        title_tag = soup.select_one('div.product-name h1')
        title = title_tag.get_text(strip=True) if title_tag else "Без названия"


        # Описание
        desc_block = soup.select_one('div.product-description')
        description = desc_block.get_text(strip=True) if desc_block else "Описание недоступно"

        # Главное изображение
        image_tag = soup.select_one('div.product-gallery img')
        image_url = image_tag['src'] if image_tag else None
        if image_url and image_url.startswith('/'):
            image_url = f"https://bartnikowskimeble.pl{image_url}"

        # Атрибуты
        attributes = []
        table = soup.select_one('#product-attributes table')
        if table:
            for row in table.select('tr'):
                cols = row.select('td')
                if len(cols) >= 2:
                    attr_name = cols[0].get_text(strip=True)
                    attr_value = cols[1].get_text(strip=True)
                    attributes.append({
                        "name": attr_name,
                        "options": [attr_value],
                        "visible": True,
                        "variation": False
                    })

        return jsonify({
            "title": title,
            "description": description,
            "images": [image_url] if image_url else [],
            "attributes": attributes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    return jsonify({
        "title": "Пример товара с Render",
        "description": "Описание, сгенерированное на стабильном Flask-сервере.",
        "attributes": [
            {"name": "Цвет", "options": ["Белый"], "visible": True, "variation": False}
        ],
        "images": ["example.jpg"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
