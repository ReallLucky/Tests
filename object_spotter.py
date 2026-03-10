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

# =====================================================
# HIDE STREAMLIT + CUSTOM CSS
# =====================================================
st.markdown("""
<style>

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

body{
background:#0f0f0f;
color:white;
font-family:Arial;
}

.block-container{
padding-top:90px;
}

.yt-header{
position:fixed;
top:0;
left:0;
right:0;
height:60px;
background:#0f0f0f;
border-bottom:1px solid #222;
display:flex;
align-items:center;
padding-left:20px;
z-index:1000;
}

.logo{
font-size:22px;
font-weight:bold;
color:#ff0000;
}

.sidebar{
position:fixed;
top:60px;
left:0;
width:200px;
bottom:0;
background:#0f0f0f;
border-right:1px solid #222;
padding-top:20px;
}

.sidebar button{
width:160px;
margin:10px;
padding:10px;
background:#181818;
color:white;
border:none;
border-radius:8px;
cursor:pointer;
}

.sidebar button:hover{
background:#282828;
}

.content{
margin-left:220px;
padding:20px;
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

<div class="yt-header">
<div class="logo">FundTube</div>
</div>

""", unsafe_allow_html=True)

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
# UPLOAD IMAGE
# =====================================================
def upload_image(image, predicted_class):

    filename = f"{predicted_class}/{uuid.uuid4()}.jpg"

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    supabase.storage.from_("fundbilder").upload(
        filename,
        buffer.getvalue(),
        {"content-type": "image/jpeg"}
    )

    public_url = supabase.storage.from_("fundbilder").get_public_url(filename)

    return public_url

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
# NAVIGATION
# =====================================================
page = st.session_state.get("page", "Galerie")

col1, col2 = st.columns([1,1])

with col1:
    if st.button("🏠 Galerie"):
        st.session_state.page = "Galerie"

with col2:
    if st.button("📦 Neuer Fund"):
        st.session_state.page = "Upload"

page = st.session_state.get("page", "Galerie")

st.markdown('<div class="content">', unsafe_allow_html=True)

# =====================================================
# UPLOAD PAGE
# =====================================================
if page == "Upload":

    st.markdown("## 📦 Neues Fundstück hochladen")

    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg","jpeg","png"])
    camera_file = st.camera_input("Foto aufnehmen")

    image_file = uploaded_file if uploaded_file else camera_file

    if image_file:

        image = Image.open(image_file).convert("RGB")
        st.image(image, use_column_width=True)

        predicted_class, confidence = classify_image(image)

        st.markdown("### 🤖 KI-Erkennung")

        st.write("Klasse:", predicted_class)
        st.write("Confidence:", round(confidence*100,2),"%")

        tag = st.selectbox(
            "Farb Tag",
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
# GALLERY PAGE
# =====================================================
if page == "Galerie":

    st.markdown("## 🖼 Fundstücke")

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
        st.info("Keine Fundstücke vorhanden.")

    else:

        cols = st.columns(4)

        for i, entry in enumerate(entries):

            with cols[i % 4]:

                st.markdown('<div class="thumbnail">', unsafe_allow_html=True)

                st.image(entry["image_url"], use_column_width=True)

                st.markdown(
                    f"""
                    **{entry['predicted_class']}**  
                    Confidence: {round(entry['confidence']*100,2)} %  
                    Farbe: {entry['tag']}
                    """
                )

                st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)