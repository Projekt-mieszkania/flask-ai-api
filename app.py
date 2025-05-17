from flask import Flask, request, jsonify

app = Flask(__name__)

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
