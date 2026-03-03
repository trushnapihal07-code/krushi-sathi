# Krushi Sathi - Crop & Fertilizer Recommendation App

**Krushi Sathi** is a Flask-based web application that helps farmers predict suitable crops and provides fertilizer recommendations based on soil type, district, and season. The app supports multilingual translations (Marathi, Hindi, English) and integrates a MySQL database for user management and crop data.

---

## **Features**

- User **signup and login** with email or phone.
- **Dashboard** showing crop recommendations.
- **Crop prediction** using a pre-trained ML model.
- **Fertilizer recommendations** based on crop and soil.
- Multilingual support: **Marathi, Hindi, English**.
- Uses **Flask** for backend and **MySQL** for database.
- Handles **dynamic dropdowns** for districts, talukas, crops, soils.

---

## **Project Structure**
krushi_flask/
│
├── app.py # Main Flask app
├── requirements.txt # Python dependencies
├── templates/ # HTML templates
│ ├── index.html
│ ├── login.html
│ ├── signup.html
│ ├── dashboard.html
│ ├── crop_info.html
│ └── fertilize.html
├── static/ # CSS, JS, images
│ ├── css/
│ ├── js/
│ └── images/
├── model_crop.pkl # ML model for crop prediction
├── le_district.pkl # LabelEncoder for districts
├── le_taluka.pkl # LabelEncoder for talukas
├── le_season.pkl # LabelEncoder for seasons
├── le_crop.pkl # LabelEncoder for crops
└── translations.json # Language translations
