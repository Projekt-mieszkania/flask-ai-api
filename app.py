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

def clean_text(text):
    return text.replace("\n", " ").replace("\r", "").strip()

def clean_and_split_attributes(raw_attributes):
    import re
    seen = set()
    final_attrs = []
    blacklist = [
        'dodaj do koszyka', 'zobacz produkt', 'zapytaj o cenę',
        'cookie', 'facebook', 'google', '@', 'regulamin', 'polityka', 'projekt i realizacja'
    ]

    for attr in raw_attributes:
        name = attr.get("name", "").strip()
        value = attr.get("options", [""])[0].strip()

        if len(value) > 200 or any(bad in value.lower() for bad in blacklist):
            continue
        if any(bad in name.lower() for bad in blacklist):
            continue

        # Разбиваем подстроки по переносам или пробелам
        lines = value.splitlines() + value.split(" ")
        for line in lines:
            if ":" in line:
                key, val = map(str.strip, line.split(":", 1))
                key = key.capitalize()
                val = val.strip()
                pair = (key.lower(), val.lower())
                if pair not in seen and val:
                    seen.add(pair)
                    final_attrs.append({
                        "name": key,
                        "options": [val],
                        "slug": "",
                        "visible": True,
                        "variation": False
                    })

        if ":" not in value and len(value) < 100:
            key = name.capitalize()
            val = value
            pair = (key.lower(), val.lower())
            if pair not in seen:
                seen.add(pair)
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

        title = soup.find("h1")
        title = title.get_text(strip=True) if title else "Bez nazwy"

        desc_tag = soup.find("div", class_="product-description") or soup.find("div", class_="description")
        description = desc_tag.get_text(strip=True) if desc_tag else f"{title} to nowoczesny produkt."

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
