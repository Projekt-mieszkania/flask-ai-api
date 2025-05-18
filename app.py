from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = Flask(__name__)

PARSING_TEMPLATES = {
    "momastudio.pl": {
        "title": "h1.product_title",
        "description": "div.woocommerce-product-details__short-description",
        "image": "figure.woocommerce-product-gallery__wrapper img"
    },
    "bartnikowskimeble.pl": {
        "title": "h1.productname",
        "description": "div.product-description",
        "image": "div#photo img",
        "attributes": "table.product-parameters"
    }
}

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        domain = urlparse(url).netloc.replace("www.", "")
        selectors = PARSING_TEMPLATES.get(domain)

        if not selectors:
            return jsonify({"error": f"Неизвестный сайт: {domain}"}), 400

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Название
        title_tag = soup.select_one(selectors.get("title", ""))
        title = title_tag.get_text(strip=True) if title_tag else "Без названия"

        # Описание
        desc_block = soup.select_one(selectors.get("description", ""))
        description = desc_block.get_text(strip=True) if desc_block else "Описание недоступно"

        # Изображения
        images = []
        for img_tag in soup.select(selectors.get("image", "")):
            img_url = img_tag.get("src")
            if img_url and img_url.startswith("/"):
                img_url = f"https://{domain}{img_url}"
            if img_url:
                images.append(img_url)

        # Атрибуты
        attributes = []
        attr_table = selectors.get("attributes")
        if attr_table:
            table = soup.select_one(attr_table)
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
            "images": images,
            "attributes": attributes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
ask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Название
        title_tag = soup.select_one('h1.productname')
        title = title_tag.get_text(strip=True) if title_tag else "Без названия"

        # Описание
        desc_block = soup.select_one('div.product-description')
        description = desc_block.get_text(strip=True) if desc_block else "Описание недоступно"

        # Изображение
        image_tag = soup.select_one('div#photo img')
        image_url = image_tag['src'] if image_tag and image_tag.has_attr('src') else None
        if image_url and image_url.startswith('/'):
            image_url = f"https://bartnikowskimeble.pl{image_url}"

        # Атрибуты
        attributes = []
        table = soup.select_one('table.product-parameters')
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

app = Flask(__name__)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")

    try:
        headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"
}
        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, 'html.parser')

        # Название
        title_tag = soup.select_one('h1.productname')
        title = title_tag.get_text(strip=True) if title_tag else "Без названия"

        # Описание
        desc_block = soup.select_one('div.product-description')
        description = desc_block.get_text(strip=True) if desc_block else "Описание недоступно"

        # Изображение
        image_tag = soup.select_one('div#photo img')
        image_url = image_tag['src'] if image_tag and image_tag.has_attr('src') else None
        if image_url and image_url.startswith('/'):
            image_url = f"https://bartnikowskimeble.pl{image_url}"

        # Атрибуты
        attributes = []
        table = soup.select_one('table.product-parameters')
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
