from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
import os
import requests
from datetime import datetime, timezone
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize OpenAI and Notion API
api_key = os.getenv('API_KEY')
client = OpenAI()
notion_api = os.getenv('NOTION_API_KEY')
notion_database_id = os.getenv('NOTION_DATABASE_ID')

headers = {
    "Authorization": f"Bearer {notion_api}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def create_page(data: dict):
    url = f"https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": notion_database_id},
        "properties": data,
    }
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    return data

@app.route('/process', methods=['POST'])
def process_article():
    content = request.json
    page_url = content.get('url')

    # Generate title using OpenAI
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": f"I'm creating a page for this article {page_url}, what should be the title of it? Reply only with the title"}
        ]
    )
    result = completion.choices[0].message.content

    name = result.strip()
    date = datetime.now(timezone.utc).isoformat()

    data = {
        "Name": {"title": [{"text": {"content": name}}]},
        "URL": {"rich_text": [{"text": {"content": page_url, "link": {"url": page_url}}}]},
        "Date": {"date": {"start": date}},
    }

    notion_response = create_page(data)
    return jsonify({"message": "Successfully created page", "data": notion_response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
