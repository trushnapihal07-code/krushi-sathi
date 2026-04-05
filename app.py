from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_cors import CORS
import pickle
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT")
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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
# OTHER ROUTES (FIXED CURSOR)
# ==============================
@app.route("/crops")
def get_crops():
    lang = request.args.get("lang", "mr")
    column_map = {"en": "crop_name_en", "hi": "crop_name_hi", "mr": "crop_name_mr"}
    column = column_map.get(lang, "crop_name_en")

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(f"""
        SELECT crop_name_en AS value,
               {column} AS label
        FROM crop_translations
        ORDER BY crop_name_en
    """)

    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/soils")
def get_soils():
    lang = request.args.get("lang", "mr")
    column_map = {"en": "soil_type_en", "hi": "soil_type_hi", "mr": "soil_type_mr"}
    column = column_map.get(lang, "soil_type_en")

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(f"""
        SELECT soil_type_en AS value,
               {column} AS label
        FROM soil_translations
        ORDER BY soil_type_en
    """)

    data = cursor.fetchall()
    conn.close()
    return jsonify(data)

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
