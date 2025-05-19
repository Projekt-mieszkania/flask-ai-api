from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

app = Flask(__name__)

# Используем более лёгкую модель
rephraser = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

import requests

def rewrite_description(text):
    try:
        res = requests.post(
            "https://Apalkova-product-rewriter.hf.space/run/predict",
            json={"data": [text]},
            timeout=20
        )
        response = res.json()
        return response["data"][0]
    except Exception as e:
        return text.strip()  # если произошла ошибка — вернём оригинал

def is_garbage(text):
    return (
        "var" in text or "=" in text or ";" in text or
        "{" in text or "}" in text or len(text) > 300 or
        not any(c.isalnum() for c in text)
    )

def clean_text(text):
    return text.replace("\n", " ").replace("\r", "").strip()

def clean_and_split_attributes(raw_attributes):
    seen = set()
    final_attrs = []
    blacklist = ['dodaj do koszyka', 'zobacz produkt', 'cookie', 'facebook', '@', 'polityka', 'regulamin']

    for attr in raw_attributes:
        name = attr.get("name", "").strip()
        value = attr.get("options", [""])[0].strip()

        if any(b in name.lower() for b in blacklist) or any(b in value.lower() for b in blacklist):
            continue

        lines = value.splitlines() + value.split(" ")
        for line in lines:
            if ":" in line:
                key, val = map(str.strip, line.split(":", 1))
                pair = (key.lower(), val.lower())
                if pair not in seen and val:
                    seen.add(pair)
                    final_attrs.append({
                        "name": key.capitalize(),
                        "options": [val],
                        "slug": "",
                        "visible": True,
                        "variation": False
                    })

        if ":" not in value and len(value) < 100:
            pair = (name.lower(), value.lower())
            if pair not in seen:
                seen.add(pair)
                final_attrs.append({
                    "name": name.capitalize(),
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

