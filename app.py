from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_cors import CORS
import mysql.connector
import pickle
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================
# CREATE APP
# ==============================
app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['JSON_AS_ASCII'] = False
CORS(app)

# ==============================
# LOAD TRANSLATIONS
# ==============================
with open("translations.json", "r", encoding="utf-8") as f:
    translations = json.load(f)

crop_translations = {
    "mr": {
        "Pulses": "डाळी",
        "Wheat": "गहू",
        "Rice": "तांदूळ",
        "Cotton": "कापूस"
    },
    "hi": {
        "Pulses": "दालें",
        "Wheat": "गेहूं",
        "Rice": "चावल",
        "Cotton": "कपास"
    }
}

soil_translations = {
    "mr": {
        "Red Soil": "लाल माती",
        "Black Soil": "काळी माती",
        "Alluvial Soil": "गाळ माती",
        "Laterite Soil": "लेटेराइट माती"
    },
    "hi": {
        "Red Soil": "लाल मिट्टी",
        "Black Soil": "काली मिट्टी",
        "Alluvial Soil": "जलोढ़ मिट्टी",
        "Laterite Soil": "लेटेराइट मिट्टी"
    }
}

season_translations = {
    "mr": {
        "Kharif": "खरीप",
        "Rabi": "रब्बी",
        "Summer": "उन्हाळा"
    },
    "hi": {
        "Kharif": "खरीफ",
        "Rabi": "रबी",
        "Summer": "गर्मी"
    }
}

# ==============================
# DATABASE CONNECTION
# ==============================
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        database=os.environ.get("DB_NAME")
    )

# ==============================
# LOAD ML MODELS
# ==============================
model = pickle.load(open("model_crop.pkl", "rb"))
le_district = pickle.load(open("le_district.pkl", "rb"))
le_taluka = pickle.load(open("le_taluka.pkl", "rb"))
le_season = pickle.load(open("le_season.pkl", "rb"))
le_crop = pickle.load(open("le_crop.pkl", "rb"))

# ==============================
# SOIL ASSIGNMENT
# ==============================
def assign_soil(district):
    black_soil = ["Pune", "Nagpur", "Nashik", "Wardha"]
    laterite = ["Ratnagiri"]
    alluvial = ["Mumbai"]

    if district in black_soil:
        return "Black Soil"
    elif district in laterite:
        return "Laterite Soil"
    elif district in alluvial:
        return "Alluvial Soil"
    else:
        return "Red Soil"

# ==============================
# HOME
# ==============================
@app.route("/")
def home():
    return render_template("index.html")

# ==============================
# SIGNUP
# ==============================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            conn.close()
            flash("Email already registered!")
            return redirect("/signup")

        cursor.execute(
            "INSERT INTO users (name, email, phone, password) VALUES (%s,%s,%s,%s)",
            (name, email, phone, password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")

# ==============================
# LOGIN
# ==============================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":

        login_id = request.form["login_id"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s OR phone=%s",
            (login_id, login_id)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            if check_password_hash(user["password"], password):
                session["user"] = user["name"]
                return redirect("/dashboard")
            else:
                flash("Wrong password!")
                return redirect("/login")
        else:
            flash("User not found!")
            return redirect("/login")

    return render_template("login.html")

# ==============================
# DASHBOARD
# ==============================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", user=session["user"])

# ==============================
# CROP INFO PAGE
# ==============================
@app.route("/crop_info")
def crop_info():
    if "user" not in session:
        return redirect("/login")
    return render_template("crop_info.html")

# ==============================
# FERTILIZER PAGE
# ==============================
@app.route("/fertilizer")
def fertilizer():
    if "user" not in session:
        return redirect("/login")
    return render_template("fertilize.html")

# ==============================
# GET DROPDOWN OPTIONS
# ==============================
@app.route("/get-options", methods=["GET"])
def get_options():

    lang = request.args.get("lang", "mr")

    districts = list(le_district.classes_)
    talukas = list(le_taluka.classes_)
    seasons = list(le_season.classes_)

    return jsonify({
        "districts": [
            {
                "label": translations.get(lang, {}).get("districts", {}).get(d, d),
                "value": d
            }
            for d in districts
        ],
        "talukas": [
            {
                "label": translations.get(lang, {}).get("talukas", {}).get(t, t),
                "value": t
            }
            for t in talukas
        ],
        "seasons": [
            {
                "label": season_translations.get(lang, {}).get(s, s),
                "value": s
            }
            for s in seasons
        ]
    })

# ==============================
# PREDICT CROP
# ==============================
@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    district = data.get("district")
    taluka = data.get("taluka")
    season = data.get("season")
    lang = data.get("lang", "mr")

    try:
        district_encoded = le_district.transform([district])[0]
        taluka_encoded = le_taluka.transform([taluka])[0]
        season_encoded = le_season.transform([season])[0]

        prediction = model.predict([[district_encoded, taluka_encoded, season_encoded]])
        crop = le_crop.inverse_transform(prediction)[0]

        soil = assign_soil(district)

        if lang in crop_translations and crop in crop_translations[lang]:
            crop = crop_translations[lang][crop]

        if lang in soil_translations and soil in soil_translations[lang]:
            soil = soil_translations[lang][soil]

        return jsonify({
            "crop": crop,
            "soil": soil
        })

    except Exception as e:
        return jsonify({"error": str(e)})
# ==============================
# FERTILIZER - GET CROPS
# ==============================
@app.route("/crops")
def get_crops():

    lang = request.args.get("lang", "mr")

    column_map = {
        "en": "crop_name_en",
        "hi": "crop_name_hi",
        "mr": "crop_name_mr"
    }

    column = column_map.get(lang, "crop_name_en")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        query = f"""
            SELECT crop_name_en AS value,
                   {column} AS label
            FROM crop_translations
            ORDER BY crop_name_en
        """

        cursor.execute(query)
        data = cursor.fetchall()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        conn.close()


# ==============================
# FERTILIZER - GET SOILS
# ==============================
@app.route("/soils")
def get_soils():

    lang = request.args.get("lang", "mr")

    column_map = {
        "en": "soil_type_en",
        "hi": "soil_type_hi",
        "mr": "soil_type_mr"
    }

    column = column_map.get(lang, "soil_type_en")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        query = f"""
            SELECT soil_type_en AS value,
                   {column} AS label
            FROM soil_translations
            ORDER BY soil_type_en
        """

        cursor.execute(query)
        data = cursor.fetchall()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        conn.close()


# ==============================
# FERTILIZER - RECOMMENDATION
# ==============================
@app.route("/recommend")
def recommend():

    crop = request.args.get("crop")
    soil = request.args.get("soil")
    lang = request.args.get("lang", "mr")

    if not crop or not soil:
        return jsonify({"error": "Crop and Soil required"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                ct.crop_name_en, ct.crop_name_hi, ct.crop_name_mr,
                st.soil_type_en, st.soil_type_hi, st.soil_type_mr,
                f.recommended_npk,
                f.chemical_fertilizer,
                f.organic_fertilizer,
                f.bio_fertilizer,
                f.application_stage
            FROM fertilizer_rules f
            JOIN crops c ON f.crop_category = c.crop_category
            JOIN crop_translations ct ON c.crop_name = ct.crop_name_en
            JOIN soil_translations st ON f.soil_type = st.soil_type_en
            WHERE ct.crop_name_en = %s
              AND st.soil_type_en = %s
        """, (crop, soil))

        r = cursor.fetchone()

        if not r:
            return jsonify({"error": "No recommendation found"}), 404

        # Language selection
        if lang == "hi":
            crop_name = r["crop_name_hi"]
            soil_name = r["soil_type_hi"]
        elif lang == "mr":
            crop_name = r["crop_name_mr"]
            soil_name = r["soil_type_mr"]
        else:
            crop_name = r["crop_name_en"]
            soil_name = r["soil_type_en"]

        return jsonify({
            "crop": crop_name,
            "soil": soil_name,
            "npk": r["recommended_npk"],
            "chemical": r["chemical_fertilizer"],
            "organic": r["organic_fertilizer"],
            "bio": r["bio_fertilizer"],
            "stage": r["application_stage"]
        })

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        conn.close()
# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ==============================
# RUN APP
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets PORT
    app.run(host="0.0.0.0", port=port)
