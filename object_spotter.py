import streamlit as st
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image, ImageOps
from supabase import create_client
import uuid
import io

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Digitales Fundbüro", layout="wide")

# Supabase Secrets (Streamlit Cloud kompatibel)
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# LOAD MODEL
# =====================================================
@st.cache_resource
def load_tm_model():
    model = load_model("keras_model.h5", compile=False)
    class_names = open("labels.txt", "r").readlines()
    return model, class_names

model, class_names = load_tm_model()

# =====================================================
# IMAGE CLASSIFICATION
# =====================================================
def classify_image(image):
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)

    image_array = np.asarray(image)
    normalized = (image_array.astype(np.float32) / 127.5) - 1

    data = np.ndarray((1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized

    prediction = model.predict(data)
    index = np.argmax(prediction)
    confidence = float(prediction[0][index])
    predicted_class = class_names[index][2:].strip()

    return predicted_class, confidence

# =====================================================
# UPLOAD IMAGE TO SUPABASE STORAGE
# =====================================================
def upload_image(image, predicted_class):

    filename = f"{predicted_class}/{uuid.uuid4()}.jpg"

    # 🔥 Sicherstellen dass es echtes RGB JPEG ist
    image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)

    supabase.storage.from_("fundbilder").upload(
        filename,
        buffer.getvalue(),
        file_options={"content-type": "image/jpeg"}
    )

    public_url = supabase.storage.from_("fundbilder") \
        .get_public_url(filename)["publicUrl"]

    return public_urlÏ

# =====================================================
# SAVE METADATA
# =====================================================
def save_metadata(image_url, predicted_class, confidence, tag):

    data = {
        "image_url": image_url,
        "predicted_class": predicted_class,
        "confidence": confidence,
        "tag": tag
    }

    supabase.table("fundstuecke").insert(data).execute()

# =====================================================
# LOAD ENTRIES
# =====================================================
def load_entries(class_filter=None, tag_filter=None):

    query = supabase.table("fundstuecke").select("*").order("created_at", desc=True)

    if class_filter and class_filter != "Alle":
        query = query.eq("predicted_class", class_filter)

    if tag_filter and tag_filter != "Alle":
        query = query.eq("tag", tag_filter)

    response = query.execute()
    return response.data

# =====================================================
# SIDEBAR NAVIGATION
# =====================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Seite wählen", ["Neuer Fund", "Galerie"])

# =====================================================
# PAGE 1 – NEUER FUND
# =====================================================
if page == "Neuer Fund":

    st.title("📦 Neuer Fund")

    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "jpeg", "png"])
    camera_file = st.camera_input("Oder Foto aufnehmen")

    image_file = uploaded_file if uploaded_file else camera_file

    if image_file:
        image = Image.open(image_file).convert("RGB")
        st.image(image, caption="Vorschau", use_column_width=True)

        predicted_class, confidence = classify_image(image)

        st.subheader("🤖 KI-Erkennung")
        st.write(f"**Klasse:** {predicted_class}")
        st.write(f"Confidence: {round(confidence * 100, 2)} %")

        tag = st.selectbox(
            "Farb-Tag auswählen",
            ["rot", "blau", "grün", "gelb", "schwarz", "weiß"]
        )

        if st.button("Speichern"):
            image_url = upload_image(image, predicted_class)
            save_metadata(image_url, predicted_class, confidence, tag)
            st.success("Fund erfolgreich gespeichert!")

# =====================================================
# PAGE 2 – GALERIE
# =====================================================
if page == "Galerie":

    st.title("🖼 Galerie")

    class_filter = st.selectbox(
        "Nach Klasse filtern",
        ["Alle", "Hoodie", "Pants", "Shoes"]
    )

    tag_filter = st.selectbox(
        "Nach Farb-Tag filtern",
        ["Alle", "rot", "blau", "grün", "gelb", "schwarz", "weiß"]
    )

    entries = load_entries(class_filter, tag_filter)

    if not entries:
        st.info("Keine Einträge gefunden.")
    else:
        cols = st.columns(3)

        for i, entry in enumerate(entries):
            with cols[i % 3]:
                st.image(entry["image_url"], use_column_width=True)
                st.write(f"**Klasse:** {entry['predicted_class']}")
                st.write(f"Confidence: {round(entry['confidence'] * 100, 2)} %")
                st.write(f"Farbe: {entry['tag']}")
                st.markdown("---")