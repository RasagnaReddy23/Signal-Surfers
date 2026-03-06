import os
import json
import uuid
from flask import Flask, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from dotenv import load_dotenv
from groq import Groq
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Configurations
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def detect_skin_tone(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return {"category": "Medium", "hex": "#e0ac69", "rgb": [224, 172, 105]}
    
    # Resize for faster processing
    img = cv2.resize(img, (300, 300))
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define skin color bounds in HSV
    lower_skin = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    
    # Extract skin mask
    mask = cv2.inRange(img_hsv, lower_skin, upper_skin)
    
    # Calculate average color of skin pixels
    if cv2.countNonZero(mask) > 0:
        mean_bgr = cv2.mean(img, mask=mask)[:3]
        mean_rgb = [int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0])]
    else:
        # Fallback to center region
        h, w, _ = img.shape
        center_region = img[h//2-50:h//2+50, w//2-50:w//2+50]
        mean_bgr = cv2.mean(center_region)[:3]
        mean_rgb = [int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0])]

    # Determine category based on luminance
    luminance = (0.299 * mean_rgb[0] + 0.587 * mean_rgb[1] + 0.114 * mean_rgb[2])
    
    if luminance > 190:
        category = "Fair"
    elif luminance > 140:
        category = "Medium"
    elif luminance > 90:
        category = "Olive"
    else:
        category = "Deep"
        
    hex_color = "#{:02x}{:02x}{:02x}".format(mean_rgb[0], mean_rgb[1], mean_rgb[2])
    
    return {"category": category, "hex": hex_color, "rgb": mean_rgb}

def get_fashion_recommendations(skin_category, gender, image_path):
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        base64_image = ""
        
    prompt = f"""
    You are a professional AI fashion stylist. The user is a {gender} with {skin_category} skin tone.
    Analyze the user's fashion style from the uploaded image and generate personalized recommendations.

    IMPORTANT RULES:
    1. Your recommendations must depend on the detected skin tone and must change for different users.
    2. Provide a fashion rating for the person's current outfit from 1 to 10 based on color harmony, fit, and style.
    3. The rating must vary depending on the outfit seen in the image.
    4. Suggest clothing colors that best match the detected skin tone.
    5. When recommending clothing items (shirt, pants, shoes), ensure the product color matches the recommended palette.
    6. If you recommend an olive shirt, the product suggestion must also be an olive shirt, not random colors.
    7. Make recommendations unique and avoid repeating the same suggestions for every input image.

    Return the response in the following structured format as JSON ONLY:
    {{
        "style_rating": {{
            "score": "X/10",
            "explanation": "Rate the person's current outfit from 1 to 10 and briefly explain why."
        }},
        "color_palette": ["Color 1", "Color 2", "Color 3", "Color 4"],
        "outfit_recommendations": {{
            "casual": "Detailed description including specific colors for shirt, pants, and shoes.",
            "office_formal": "Detailed description including specific colors.",
            "party": "Detailed description including specific colors."
        }},
        "product_suggestions": {{
            "shirt": "Specific condition and color",
            "pants": "Specific condition and color",
            "shoes": "Specific condition and color",
            "accessories": "Specific condition and color"
        }},
        "style_feedback": "Short personalized fashion advice to improve the person's style.",
        "motivational_fashion_quote": "Give a short inspirational fashion quote."
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.7
        )
        content = completion.choices[0].message.content
        # In case the model surrounds JSON with backticks, clean it
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        # Fallback response
        return {
            "style_rating": {
                "score": "7/10",
                "explanation": "A safe and classic style, though it lacks a distinct focal point."
            },
            "color_palette": ["Navy Blue", "Olive Green", "Burgundy", "Mustard Yellow"],
            "outfit_recommendations": {
                "casual": "Classic white t-shirt with dark wash denim and white sneakers.",
                "office_formal": "Charcoal grey suit with a crisp light blue shirt and leather shoes.",
                "party": "Sleek monochromatic outfit with subtle metallic accents."
            },
            "product_suggestions": {
                "shirt": "Navy Blue slim-fit Oxford shirt",
                "pants": "Olive Green tailored chinos",
                "shoes": "Dark brown leather loafers",
                "accessories": "Minimalist silver watch"
            },
            "style_feedback": "Try incorporating more contrast into your outfits. A structured jacket can add definition to your shoulders.",
            "motivational_fashion_quote": "Style is a way to say who you are without having to speak. - Rachel Zoe"
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
        
    file = request.files['image']
    gender = request.form.get('gender', 'Female')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        # Add uuid to prevent collisions
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # 1. Detect Skin Tone
        skin_tone_data = detect_skin_tone(filepath)
        
        # 2. Get AI Recommendations
        recommendations = get_fashion_recommendations(skin_tone_data['category'], gender, filepath)
        
        # Cleanup file after processing
        try:
            os.remove(filepath)
        except:
            pass
            
        return jsonify({
            "success": True,
            "skin_tone": skin_tone_data,
            "recommendations": recommendations
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
