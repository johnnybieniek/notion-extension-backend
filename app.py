from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
import os
import requests
from datetime import datetime, timezone
from flask_cors import CORS
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

# Initialize OpenAI and Notion API
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()
notion_api = os.getenv('NOTION_API_KEY')

database_ids = {
    'personal': os.getenv('NOTION_DATABASE_ID_PERSONAL'),
    'research': os.getenv('NOTION_DATABASE_ID_RESEARCH'),
    'shopping': os.getenv('NOTION_DATABASE_ID_SHOPPING')
}

headers = {
    "Authorization": f"Bearer {notion_api}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def generate_research_data(page_url):
    prompt = f"""
    As a senior researcher, extract the following information from this article {page_url} and return it in JSON format:
    1. Title
    2. Tags (choose one of the following: Other, Research paper, Article, Book)
    3. TL;DR (a concise summary of what's in the link)
    4. Relevance
    Example response:
    {{
        "title": "Example Title",
        "tags": "Research paper",
        "tldr": "This is a brief summary.",
        "relevance": "This article is highly relevant for research purposes because..."
    }}
    """
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    result = json.loads(completion.choices[0].message.content.strip())
    return result
    

def generate_shopping_data(page_url):
    prompt = f"""
    Evaluate the page"""+page_url+""" and extract the following information:
    1. Name of the item
    2. Price of the item
    3. URL to the item
    4. Based on what the item is, evaluate the urgency as "Low", "Medium", or "High"
    5. A short description of the item
    Return the information in JSON format. Example response:
    {{
        "name": "Example Item",
        "price": "$100",
        "url": """+page_url+""",
        "urgency": "Medium",
        "description": "This is a short description of the item."
    }}
    """
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    result = json.loads(completion.choices[0].message.content.strip())
    return result
   

def create_page(data: dict, database_id: str):
    url = f"https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": database_id},
        "properties": data,
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()



def process_research(page_url):
    research_data = generate_research_data(page_url)
    date = datetime.now(timezone.utc).isoformat()
    data = {
        "Title": {"title": [{"text": {"content": research_data['title']}}]},
        "Tags": {"multi_select": [{"name": research_data['tags']}]},
        "TL;DR": {"rich_text": [{"text": {"content": research_data['tldr']}}]},
        "Relevance": {"multi_select": [{"name": "Unassigned"}]},
        "Link": {"url": page_url},
        "Date": {"date": {"start": date}}
    }
    return data

def process_shopping(page_url):
    shopping_data = generate_shopping_data(page_url)
    date = datetime.now(timezone.utc).isoformat()
    data = {
        "Name": {"title": [{"text": {"content": shopping_data['name']}}]},
        "Price": {"rich_text": [{"text": {"content": shopping_data['price']}}]},
        "URL": {"url": page_url},
        "Date": {"date": {"start": date}},
        "Urgency": {"multi_select": [{"name": shopping_data['urgency']}]},
        "Description": {"rich_text": [{"text": {"content": shopping_data['description']}}]},
        "Purchased?": {"checkbox": False}
    }
    return data

@app.route('/process', methods=['POST'])
def process_article():
    content = request.json
    page_url = content.get('url')
    category = content.get('category')
    print('Category:', category)
    database_id = database_ids.get(category)

    if not database_id:
        return jsonify({"error": "Invalid category"}), 400

    # Determine the processing function based on category
    if category == 'personal':
        data = print("hello, error!")
    elif category == 'research':
        data = process_research(page_url)
    elif category == 'shopping':
        data = process_shopping(page_url)
    else:
        return jsonify({"error": "Unsupported category"}), 400

    notion_response = create_page(data, database_id)
    return jsonify({"message": "Successfully created page", "data": notion_response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
