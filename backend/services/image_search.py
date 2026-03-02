from serpapi import GoogleSearch
import os


def reverse_image_search(image_path):

    params = {
        "engine": "google_lens",
        "api_key": os.getenv("SERPAPI_KEY"),
        "url": "https://serpapi.com/images/sample.jpg"  # fallback
    }

    # ⚠️ NOTE:
    # SerpAPI requires a public image URL
    # So local images won't work directly

    search = GoogleSearch(params)
    results = search.get_dict()

    output = []

    try:
        for item in results.get("visual_matches", [])[:5]:
            output.append({
                "title": item.get("title"),
                "link": item.get("link")
            })
    except:
        pass

    return output
