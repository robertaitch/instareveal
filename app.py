from flask import Flask, request, render_template, send_file, jsonify, Response
import requests
import json
import os
import datetime

def create_app():
    app = Flask(__name__)
    return app

app = create_app()

INSTAGRAM_API_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-IG-App-ID": "936619743392459"
}

@app.route("/proxy_image", methods=["POST"])
def proxy_image():
    data = request.get_json()
    image_url = data.get('url')
    
    if not image_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.instagram.com/",
            "Accept": "image/*,*/*;q=0.8"
        }
        
        response = requests.get(image_url, headers=headers, stream=True)
        
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype=response.headers.get('content-type', 'image/jpeg'),
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            return jsonify({"error": "Failed to fetch image"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        sessionid = request.form.get("sessionid")
        csrftoken = request.form.get("csrftoken") or ""

        cookies = {"sessionid": sessionid, "csrftoken": csrftoken}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "X-CSRFToken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/{username}/",
            "X-IG-App-ID": "936619743392459",
            "Cookie": f"sessionid={sessionid}; csrftoken={csrftoken}"
        }

        r = requests.get(
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers=headers,
            cookies=cookies
        )

        if r.status_code != 200:
            return render_template("index.html", error="Failed to fetch profile")

        data = r.json().get("data", {}).get("user", {})
        user_id = data.get("id")

        email, phone = None, None
        lookup_res = requests.post(
            "https://i.instagram.com/api/v1/users/lookup/",
            headers={
                "Accept-Language": "en-US",
                "User-Agent": "Instagram 101.0.0.15.120",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-IG-App-ID": "124024574287414",
                "Accept-Encoding": "gzip, deflate",
                "Host": "i.instagram.com",
                "Connection": "keep-alive"
            },
            data="signed_body=SIGNATURE." + requests.utils.quote(json.dumps({"q": username, "skip_recovery": "1"}, separators=(",", ":")))
        )

        if lookup_res.status_code == 200:
            json_contact = lookup_res.json()
            email = json_contact.get("obfuscated_email")
            phone = json_contact.get("obfuscated_phone")

        profile_pic_url = None
        if data.get("hd_profile_pic_url_info"):
            profile_pic_url = data["hd_profile_pic_url_info"].get("url")
        if not profile_pic_url and data.get("profile_pic_url_hd"):
            profile_pic_url = data["profile_pic_url_hd"]
        if not profile_pic_url and data.get("profile_pic_url"):
            profile_pic_url = data["profile_pic_url"]
        if not profile_pic_url and data.get("profile_pic_url_https"):
            profile_pic_url = data["profile_pic_url_https"]

        profile = {
            "username": username,
            "user_id": user_id,
            "full_name": data.get("full_name"),
            "profile_pic_url": profile_pic_url,
            "is_verified": data.get("is_verified"),
            "is_private": data.get("is_private"),
            "is_business": data.get("is_business_account"),
            "is_professional": data.get("is_professional_account"),
            "account_type": data.get("account_type", "Unknown"),
            "category": data.get("category"),
            "is_joined_recently": data.get("is_joined_recently"),
            "is_memorialized": data.get("is_memorialized"),
            "followers": data.get("edge_followed_by", {}).get("count", 0),
            "following": data.get("edge_follow", {}).get("count", 0),
            "posts_count": data.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "tagged_posts": data.get("edge_user_to_photos_of_you", {}).get("count", 0),
            "highlight_reel_count": data.get("highlight_reel_count", 0),
            "igtv_count": data.get("edge_felix_video_timeline", {}).get("count", 0),
            "mutual_followers": data.get("edge_mutual_followed_by", {}).get("count", 0),
            "engagement_rate": 0.0,
            "business_email": data.get("public_email"),
            "business_phone": data.get("public_phone_country_code", '') + data.get("public_phone_number", ''),
            "public_email": data.get("public_email"),
            "public_phone": data.get("public_phone_number"),
            "obfuscated_email": email,
            "obfuscated_phone": phone,
            "biography": data.get("biography"),
            "external_url": data.get("external_url")
        }

        return render_template("profile.html", profile=profile, current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return render_template("index.html")

@app.route("/export/json", methods=["POST"])
def export_json():
    profile_data = request.get_json()
    filepath = f"/tmp/{profile_data['username']}_profile.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)
    return send_file(filepath, as_attachment=True, download_name=f"{profile_data['username']}_profile.json")

if __name__ == "__main__":
    app.run(debug=False)