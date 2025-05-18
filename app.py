from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import openai

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")

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

        # Поиск заголовка
        title = "Bez nazwy"
        for selector in ['h1', 'h1.product-title', 'h1[itemprop=name]', 'meta[property="og:title"]']:
            tag = soup.select_one(selector)
            if tag:
                title = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        # Поиск описания
        description = ""
        for selector in ['div.description', 'div.product-description', 'div[itemprop=description]', 'meta[name="description"]']:
            tag = soup.select_one(selector)
            if tag:
                description = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        # Изображения
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http"):
                images.append(src)
            if len(images) >= 3:
                break

        # Генерация SEO и описания
        prompt = f"""
Produkt: {title}
Opis strony: {description}

Wygeneruj zoptymalizowany opis produktu po polsku, metatytuł, metadescription i słowa kluczowe dla SEO.
Format odpowiedzi JSON:
{{
  "description": "...",
  "meta_title": "...",
  "meta_description": "...",
  "keywords": ["...", "..."]
}}
"""

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        content = completion.choices[0].message['content']
        import json
        seo_data = json.loads(content)

        return jsonify({
            "title": title,
            "description": seo_data["description"],
            "seo": {
                "meta_title": seo_data["meta_title"],
                "meta_description": seo_data["meta_description"],
                "keywords": seo_data["keywords"]
            },
            "images": images,
            "attributes": []
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
