from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

WC_URL = "https://projekt-mieszkania.pl"
WC_KEY = "ck_f5c91a1d42a5dc898fe3fea084d464a29b9a2466"
WC_SECRET = "cs_2d80076cdfa0e571855e1965115387ec5946495b"

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct"

def get_wc_attributes():
    try:
        response = requests.get(
            f"{WC_URL}/wp-json/wc/v3/products/attributes",
            auth=(WC_KEY, WC_SECRET),
            timeout=10
        )
        data = response.json()
        return {item["name"]: item["slug"] for item in data}
    except Exception:
        return {}

def is_garbage(text):
    return (
        "var" in text or "=" in text or ";" in text or
        "{" in text or "}" in text or len(text) > 100 or
        not any(c.isalnum() for c in text)
    )

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
    except Exception:
        return text

def extract_attributes(soup, wc_slugs):
    attributes = []

    # 1. Таблицы
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True).strip(":")
                value = cols[1].get_text(strip=True)
                if name and value and not is_garbage(name) and not is_garbage(value):
                    attributes.append({
                        "name": name,
                        "slug": wc_slugs.get(name, ""),
                        "options": [value],
                        "visible": True,
                        "variation": False
                    })

    # 2. Списки ul > li с двоеточием
    for li in soup.find_all("li"):
        if ":" in li.get_text():
            parts = li.get_text().split(":", 1)
            name, value = parts[0].strip(), parts[1].strip()
            if name and value and not is_garbage(name) and not is_garbage(value):
                attributes.append({
                    "name": name,
                    "slug": wc_slugs.get(name, ""),
                    "options": [value],
                    "visible": True,
                    "variation": False
                })

    # 3. div/p/span с двоеточием
    for tag in soup.find_all(["div", "p", "span"]):
        if ":" in tag.get_text():
            parts = tag.get_text().split(":", 1)
            name, value = parts[0].strip(), parts[1].strip()
            if name and value and not is_garbage(name) and not is_garbage(value):
                attributes.append({
                    "name": name,
                    "slug": wc_slugs.get(name, ""),
                    "options": [value],
                    "visible": True,
                    "variation": False
                })

    # 4. dt/dd из <dl>
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            name = dt.get_text(strip=True)
            value = dd.get_text(strip=True)
            if name and value and not is_garbage(name) and not is_garbage(value):
                attributes.append({
                    "name": name,
                    "slug": wc_slugs.get(name, ""),
                    "options": [value],
                    "visible": True,
                    "variation": False
                })

    return attributes

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        wc_slugs = get_wc_attributes()

        title = "Bez nazwy"
        for selector in ['h1', 'h1.product-title', 'meta[property="og:title"]']:
            tag = soup.select_one(selector)
            if tag:
                title = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        description = ""
        for selector in ['div.description', 'div.product-description', 'meta[name="description"]']:
            tag = soup.select_one(selector)
            if tag:
                description = tag.get_text(strip=True) if tag.name != 'meta' else tag.get("content", "").strip()
                break

        if not description:
            description = f"{title} to nowoczesny produkt wysokiej jakości."

        rewritten = rewrite_description(description)

        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http") and "CatImg" not in src and "icon" not in src:
                images.append(src)
            if len(images) >= 5:
                break

        attributes = extract_attributes(soup, wc_slugs)

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

