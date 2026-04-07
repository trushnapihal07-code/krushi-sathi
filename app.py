from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_cors import CORS
import pickle
import json
import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================
# CREATE APP
# ==============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallbacksecret")

app.config['JSON_AS_ASCII'] = False
CORS(app)

# ==============================
# LOAD TRANSLATIONS
# ==============================
with open("translations.json", "r", encoding="utf-8") as f:
    translations = json.load(f)

# ==============================
# DATABASE CONNECTION (SAFE ✅)
# ==============================
def get_db():
    try:
        conn = mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            port=int(os.environ.get("DB_PORT"))
        )
        return conn
    except Exception as e:
        print("DB CONNECTION ERROR:", e)
        return None

# ==============================
# LOAD ML MODELS
# ==============================
model = pickle.load(open("model_crop.pkl", "rb"))
le_district = pickle.load(open("le_district.pkl", "rb"))
le_taluka = pickle.load(open("le_taluka.pkl", "rb"))
le_season = pickle.load(open("le_season.pkl", "rb"))
le_crop = pickle.load(open("le_crop.pkl", "rb"))

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
        try:
            name = request.form["name"]
            email = request.form["email"]
            phone = request.form["phone"]
            password = generate_password_hash(request.form["password"])

            conn = get_db()
            if conn is None:
                flash("Database connection error")
                return redirect("/signup")

            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                flash("Email already registered!")
                return redirect("/signup")

            cursor.execute(
                "INSERT INTO users (name, email, phone, password) VALUES (%s,%s,%s,%s)",
                (name, email, phone, password)
            )

            conn.commit()
            cursor.close()
            conn.close()

            return redirect("/login")

        except Exception as e:
            print("SIGNUP ERROR:", e)
            flash("Something went wrong!")
            return redirect("/signup")

    return render_template("signup.html")

# ==============================
# LOGIN
# ==============================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        try:
            login_id = request.form["login_id"]
            password = request.form["password"]

            conn = get_db()
            if conn is None:
                flash("Database connection error")
                return redirect("/login")

            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE email=%s OR phone=%s",
                (login_id, login_id)
            )

            user = cursor.fetchone()

            print("Login attempt:", login_id)
            print("User found:", user)

            cursor.close()
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

        except Exception as e:
            print("LOGIN ERROR:", e)
            flash("Something went wrong!")
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
# CROPS
# ==============================
@app.route("/crops")
def get_crops():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT crop_name_en AS value,
                   crop_name_en AS label
            FROM crop_translations
            ORDER BY crop_name_en
        """)

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(data)

    except Exception as e:
        print("CROPS ERROR:", e)
        return jsonify([])

# ==============================
# SOILS
# ==============================
@app.route("/soils")
def get_soils():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT soil_type_en AS value,
                   soil_type_en AS label
            FROM soil_translations
            ORDER BY soil_type_en
        """)

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(data)

    except Exception as e:
        print("SOILS ERROR:", e)
        return jsonify([])

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
