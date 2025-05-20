from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

HF_API_URL = "https://Apalkova-product-rewriter.hf.space/run/predict"

def rewrite_description(text):
    try:
        res = requests.post(HF_API_URL, json={"data": [text]}, timeout=20)
        return res.json()["data"][0].strip()
    except Exception:
        return text.strip()

def is_garbage(text):
    garbage_signals = [
        "cookie", "facebook", "napisz", "projekt", "@", "mailto",
        "dodaj do koszyka", "zobacz produkt", "zł", "promocja", "komoda", "produkt"
    ]
    return (
        any(x in text.lower() for x in garbage_signals)
        or any(c in text for c in ["=", "{", "}", ";"])
        or len(text) > 150
        or not any(c.isalnum() for c in text)
    )

def clean_text(text):
    return text.replace("\n", " ").replace("\r", "").strip()

def extract_clean_name_value(name, value):
    match = re.match(r"(?P<num>\d{2,4})\s*cm(\s*)?(?P<txt>[a-zA-Ząćęłńóśźż]+)", name)
    if match:
        return match.group("txt").capitalize(), f"{match.group('num')} cm"
    return name.capitalize(), value.strip()

def clean_and_split_attributes(raw_attributes):
    seen = set()
    final_attrs = []

    for attr in raw_attributes:
        name_raw = clean_text(attr.get("name", ""))
        value_raw = clean_text(attr.get("options", [""])[0])

        if is_garbage(name_raw) or is_garbage(value_raw):
            continue

        name, value = extract_clean_name_value(name_raw, value_raw)
        if is_garbage(name) or is_garbage(value):
            continue

        if ":" in value:
            lines = value.splitlines() + value.split(" ")
            for line in lines:
                if ":" in line:
                    key, val = map(str.strip, line.split(":", 1))
                    key, val = extract_clean_name_value(key, val)
                    if not is_garbage(key) and not is_garbage(val):
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
        else:
            pair = (name.lower(), value.lower())
            if pair not in seen:
                seen.add(pair)
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

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "Bez nazwy"

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

