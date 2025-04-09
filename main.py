from typing import Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import time
from streamfeed import preview_feed
from urllib.parse import urlparse

app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory cache
cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes


def is_valid_url(url: str) -> bool:
    """Validate if the provided string is a proper URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in [
            "http",
            "https",
        ]
    except:
        return False


def get_cached_feed(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get feed from cache if it exists and is not expired."""
    if cache_key in cache:
        entry = cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
    return None


def cache_feed(cache_key: str, data: Dict[str, Any]):
    """Store feed data in cache."""
    cache[cache_key] = {"data": data, "timestamp": time.time()}


@app.get("/", response_class=HTMLResponse)
def pretty_preview(
    url: Optional[str] = None,
    size: int = Query(1, enum=[1, 5, 10, 20]),
    xml_item_tag: Optional[str] = None,
):
    feed_content = ""
    error_message = ""

    # If a URL is provided, try to load the feed
    if url:
        # Validate URL format
        if not is_valid_url(url):
            error_message = (
                "Invalid URL format. Please provide a valid HTTP or HTTPS URL."
            )
        else:
            feed_logic = {"xml_item_tag": xml_item_tag} if xml_item_tag else {}
            cache_key = f"{url}:{size}:{xml_item_tag}"

            # Try to get from cache first
            cached_result = get_cached_feed(cache_key)
            if cached_result:
                feed_content = json.dumps(cached_result, indent=4)
            else:
                try:
                    data = preview_feed(url=url, feed_logic=feed_logic, limit_rows=size)
                    # Cache the result
                    cache_feed(cache_key, data)
                    # Convert the feed data to pretty-printed JSON format
                    feed_content = json.dumps(data, indent=4)
                except Exception as e:
                    error_message = f"Error fetching feed: {str(e)}"

    # Prepare the conditional parts of the HTML
    url_value = url or ""
    size_1_selected = "selected" if size == 1 else ""
    size_5_selected = "selected" if size == 5 else ""
    size_10_selected = "selected" if size == 10 else ""
    size_20_selected = "selected" if size == 20 else ""
    xml_tag_value = xml_item_tag or ""

    error_html = (
        f"<div class='error'>Error: {error_message}</div>" if error_message else ""
    )
    feed_html = (
        f"<div class='output'><h2>Feed Output</h2><pre>{feed_content}</pre></div>"
        if feed_content
        else ""
    )

    # Construct the HTML page with a form and a section for output/error messages.
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Feed Preview</title>
    <meta charset="utf-8" />
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: auto;
            background: #fff;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
        }}
        .description {{
            background-color: #e9f7ef;
            border-left: 4px solid #2ecc71;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 0.95em;
        }}
        .description a {{
            color: #007BFF;
            text-decoration: none;
        }}
        .description a:hover {{
            text-decoration: underline;
        }}
        .form-group {{
            margin-bottom: 15px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
        }}
        input[type="text"], select {{
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
        }}
        input[type="submit"] {{
            padding: 10px 20px;
            background-color: #007BFF;
            color: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }}
        input[type="submit"]:hover {{
            background-color: #0056b3;
        }}
        .output {{
            white-space: pre-wrap;
            background: #eee;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 20px;
            overflow-x: auto;
        }}
        .error {{
            color: red;
            font-weight: bold;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Feed Preview</h1>
        <div class="description">
            This simple web application uses the <strong>streamfeed-parser</strong> Python library by Hans-Christian Bøge Pedersen to parse and preview XML and CSV feeds. I can both handle HTTP and FTP. You can learn more about the library on 
            <a href="https://github.com/devwithhans/streamfeed-parser?tab=readme-ov-file" target="_blank">GitHub</a> or view it on 
            <a href="https://pypi.org/project/streamfeed-parser/" target="_blank">PyPI</a>.
        </div>
        <form action="/" method="get">
            <div class="form-group">
                <label for="url">Feed URL:</label>
                <input type="text" id="url" name="url" placeholder="Enter Feed URL" value="{url_value}" required>
            </div>
            <div class="form-group">
                <label for="size">Number of Items:</label>
                <select id="size" name="size">
                    <option value="1" {size_1_selected}>1</option>
                    <option value="5" {size_5_selected}>5</option>
                    <option value="10" {size_10_selected}>10</option>
                    <option value="20" {size_20_selected}>20</option>
                </select>
            </div>
            <div class="form-group">
                <label for="xml_item_tag">XML Item Tag (Optional):</label>
                <input type="text" id="xml_item_tag" name="xml_item_tag" placeholder="e.g., item" value="{xml_tag_value}">
            </div>
            <input type="submit" value="Preview Feed">
        </form>
        {error_html}
        {feed_html}
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# Original preview endpoint that returns raw JSON
@app.get("/preview")
def preview_feed_endpoint(
    url: str,
    size: int = Query(1, enum=[1, 5, 10, 20]),
    xml_item_tag: Optional[str] = None,
):
    # Validate URL format
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL format")

    feed_logic = {"xml_item_tag": xml_item_tag} if xml_item_tag else {}
    cache_key = f"{url}:{size}:{xml_item_tag}"

    # Try to get from cache first
    cached_result = get_cached_feed(cache_key)
    if cached_result:
        return cached_result

    try:
        data = preview_feed(url=url, feed_logic=feed_logic, limit_rows=size)
        cache_feed(cache_key, data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feed: {str(e)}")


# Health check endpoint.
@app.get("/health")
def health_check():
    return {"status": "ok"}
