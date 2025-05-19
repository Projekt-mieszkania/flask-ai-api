from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def is_garbage(text):
    return (
        "var" in text or "=" in text or ";" in text or
        "{" in text or "}" in text or len(text) > 100 or
        not any(c.isalnum() for c in text)
    )

def rewrite_description(text):
    return text  # Можно подключить HuggingFace при необходимости

def clean_and_split_attributes(raw_attributes):
    seen = set()
    final_attrs = []

    for attr in raw_attributes:
        name = attr["name"].strip()
        value = attr["options"][0].strip()

        # Расщепляем составные значения с переносами строк
        if "\n" in value or "
" in value:
            for line in value.splitlines():
                if ":" in line:
                    sub_name, sub_value = line.split(":", 1)
                    sub_name = sub_name.strip()
                    sub_value = sub_value.strip()
                    key = (sub_name.lower(), sub_value.lower())
                    if key not in seen and not is_garbage(sub_name) and not is_garbage(sub_value):
                        seen.add(key)
                        final_attrs.append({
                            "name": sub_name,
                            "options": [sub_value],
                            "slug": "",
                            "visible": True,
                            "variation": False
                        })
        else:
            key = (name.lower(), value.lower())
            if key not in seen and not is_garbage(name) and not is_garbage(value):
                seen.add(key)
                final_attrs.append({
                    "name": name,
                    "options": [value],
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

        title = soup.find("h1")
        title = title.get_text(strip=True) if title else "Bez nazwy"

        desc_tag = soup.find("div", class_="product-description") or soup.find("div", class_="description")
        description = desc_tag.get_text(strip=True) if desc_tag else f"{title} to nowoczesny produkt."

        rewritten = rewrite_description(description)

        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if (
                src.startswith("http")
                and not any(x in src for x in ["logo", "icon", "facebook", "svg"])
                and any(src.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])
            ):
                images.append(src)
            if len(images) >= 5:
                break

        # Собираем все сырые атрибуты (с примитивным поиском)
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
            "description": rewritten,
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
