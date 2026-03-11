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

st.set_page_config(page_title="FundTube", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ADMIN_PASSWORD = "fundtube_admin_2026"

# =====================================================
# SESSION STATE
# =====================================================

if "page" not in st.session_state:
    st.session_state.page = "Galerie"

if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = True

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# =====================================================
# CSS DESIGN
# =====================================================

st.markdown("""
<style>

[data-testid="stAppViewContainer"]{
background: radial-gradient(circle at bottom, #000033 0%, #000000 60%);
background-repeat:no-repeat;
background-attachment:fixed;
}

section[data-testid="stSidebar"]{
background:#0f0f0f;
border-right:1px solid #222;
}

.sidebar-btn button{
width:100%;
display:block;
background:none;
border:none;
color:white;
text-align:left;
padding:12px 15px;
font-size:16px;
border-radius:8px;
margin-bottom:5px;
}

.sidebar-btn button:hover{
background:#1f1f1f;
}

.thumbnail{
background:#181818;
padding:10px;
border-radius:12px;
margin-bottom:20px;
transition:0.2s;
}

.thumbnail:hover{
transform:scale(1.03);
}

img{
border-radius:10px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================

if st.button("☰"):
    st.session_state.sidebar_state = not st.session_state.sidebar_state

if st.session_state.sidebar_state:

    with st.sidebar:

        st.title("FundTube")

        st.markdown('<div class="sidebar-btn">', unsafe_allow_html=True)

        if st.button("🏠 Galerie"):
            st.session_state.page = "Galerie"

        if st.button("📦 Neuer Fund"):
            st.session_state.page = "Upload"

        if st.button("🔐 Admin"):
            st.session_state.page = "Admin"

        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# MODEL LADEN
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

    size = (224,224)

    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)

    image_array = np.asarray(image)

    normalized = (image_array.astype(np.float32)/127.5)-1

    data = np.ndarray((1,224,224,3), dtype=np.float32)

    data[0] = normalized

    prediction = model.predict(data)

    index = np.argmax(prediction)

    confidence = float(prediction[0][index])

    predicted_class = class_names[index][2:].strip()

    return predicted_class, confidence

# =====================================================
# IMAGE UPLOAD
# =====================================================

def upload_image(image, predicted_class):

    filename = f"{predicted_class}/{uuid.uuid4()}.jpg"

    buffer = io.BytesIO()

    image.save(buffer, format="JPEG")

    buffer.seek(0)

    supabase.storage.from_("fundbilder").upload(
        filename,
        buffer.getvalue(),
        {"content-type":"image/jpeg"}
    )

    public_url = supabase.storage.from_("fundbilder").get_public_url(filename)

    return public_url

# =====================================================
# METADATA SPEICHERN
# =====================================================

def save_metadata(url, predicted_class, confidence, tag):

    data = {
        "image_url":url,
        "predicted_class":predicted_class,
        "confidence":confidence,
        "tag":tag
    }

    supabase.table("fundstuecke").insert(data).execute()

# =====================================================
# EINTRÄGE LADEN
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
# EINTRAG LÖSCHEN
# =====================================================

def delete_entry(entry):

    image_url = entry["image_url"]

    path = image_url.split("/fundbilder/")[1]

    supabase.storage.from_("fundbilder").remove([path])

    supabase.table("fundstuecke").delete().eq("id", entry["id"]).execute()

# =====================================================
# PAGE ROUTER
# =====================================================

page = st.session_state.page

# =====================================================
# GALERIE
# =====================================================

if page == "Galerie":

    st.markdown("""
    ## 👋 Willkommen bei FundTube

    FundTube hilft verlorene Kleidung wiederzufinden.

    **So funktioniert es:**

    1️⃣ Menschen laden gefundene Kleidung hoch  
    2️⃣ Eine KI erkennt automatisch die Kategorie  
    3️⃣ Ein Farb-Tag wird hinzugefügt  
    4️⃣ Andere können sehen, dass die Kleidung gefunden wurde
    """)

    st.divider()

    st.header("🖼 Fundstücke")

    class_filter = st.selectbox(
        "Kategorie",
        ["Alle","Hoodie","Pants","Shoes"]
    )

    tag_filter = st.selectbox(
        "Farb Tag",
        ["Alle","rot","blau","grün","gelb","schwarz","weiß"]
    )

    entries = load_entries(class_filter, tag_filter)

    if not entries:

        st.info("Keine Fundstücke vorhanden")

    else:

        cols = st.columns(4)

        for i,entry in enumerate(entries):

            with cols[i%4]:

                st.markdown('<div class="thumbnail">', unsafe_allow_html=True)

                st.image(entry["image_url"], use_column_width=True)

                st.markdown(f"""
                **{entry['predicted_class']}**

                Confidence: {round(entry['confidence']*100,2)} %

                Farbe: {entry['tag']}
                """)

                st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# UPLOAD PAGE
# =====================================================

if page == "Upload":

    st.header("📦 Neues Fundstück")

    upload_tab, camera_tab = st.tabs(
        ["📤 Datei hochladen","📷 Kamera"]
    )

    image_file = None

    with upload_tab:

        uploaded_file = st.file_uploader(
            "Bild auswählen",
            type=["jpg","jpeg","png"]
        )

        if uploaded_file:
            image_file = uploaded_file

    with camera_tab:

        camera_file = st.camera_input("Foto aufnehmen")

        if camera_file:
            image_file = camera_file

    if image_file:

        image = Image.open(image_file).convert("RGB")

        st.image(image, caption="Vorschau", use_column_width=True)

        predicted_class, confidence = classify_image(image)

        st.subheader("🤖 KI-Erkennung")

        st.write("Klasse:", predicted_class)

        st.write("Confidence:", round(confidence*100,2), "%")

        tag = st.selectbox(
            "Farb Tag auswählen",
            ["rot","blau","grün","gelb","schwarz","weiß"]
        )

        if st.button("Speichern"):

            image_url = upload_image(image, predicted_class)

            save_metadata(
                image_url,
                predicted_class,
                confidence,
                tag
            )

            st.success("Fundstück gespeichert!")

# =====================================================
# ADMIN PAGE
# =====================================================

if page == "Admin":

    st.header("🔐 Admin Bereich")

    if not st.session_state.admin_logged_in:

        password = st.text_input(
            "Admin Passwort",
            type="password"
        )

        if st.button("Login"):

            if password == ADMIN_PASSWORD:

                st.session_state.admin_logged_in = True

                st.success("Login erfolgreich")

                st.rerun()

            else:

                st.error("Falsches Passwort")

    else:

        st.success("Admin angemeldet")

        if st.button("Logout"):

            st.session_state.admin_logged_in = False

            st.rerun()

        st.divider()

        entries = load_entries()

        if not entries:

            st.info("Keine Einträge")

        else:

            cols = st.columns(3)

            for i,entry in enumerate(entries):

                with cols[i%3]:

                    st.image(entry["image_url"], use_column_width=True)

                    st.write("Klasse:",entry["predicted_class"])

                    st.write("Tag:",entry["tag"])

                    if st.button("🗑 Löschen", key=f"delete_{entry['id']}"):

                        delete_entry(entry)

                        st.warning("Eintrag gelöscht")

                        st.rerun()