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
# CSS DESIGN
# =====================================================
st.markdown("""
<style>
/* Header komplett ausblenden */
header {visibility:hidden;}
footer {visibility:hidden;}

/* App Hintergrund: radialer Farbverlauf */
[data-testid="stAppViewContainer"]{
background: radial-gradient(circle at bottom, #000033 0%, #000000 60%);
background-attachment: fixed;
}

/* Sidebar */
section[data-testid="stSidebar"]{
background:#0f0f0f;
border-right:1px solid #222;
}

/* Sidebar Buttons */
.sidebar-btn button{
width:100%;
background:none;
border:none;
color:white;
text-align:left;
padding:10px 15px;
font-size:16px;
border-radius:8px;
}

.sidebar-btn button:hover{
background:#1f1f1f;
}

/* Upload Tabs oben abgerundet */
button[data-baseweb="tab"]{
background:#181818;
border-radius:12px 12px 0px 0px;
border:none;
color:white;
}

button[data-baseweb="tab"]:hover{
background:#2a2a2a;
}

button[data-baseweb="tab"][aria-selected="true"]{
background:#181818;
color:white;
border:none;
}

/* Thumbnails */
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
# SESSION STATE FÜR PAGE
# =====================================================
if "page" not in st.session_state:
    st.session_state.page = "Galerie"

# =====================================================
# SIDEBAR BUTTONS
# =====================================================
with st.sidebar:
    st.title("FundTube")
    st.markdown('<div class="sidebar-btn">', unsafe_allow_html=True)
    if st.button("🏠 Galerie"):
        st.session_state.page = "Galerie"
    if st.button("📦 Neuer Fund"):
        st.session_state.page = "Upload"
    st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.page

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
    image = ImageOps.fit(image,size,Image.Resampling.LANCZOS)
    arr = np.asarray(image)
    normalized = (arr.astype(np.float32)/127.5)-1
    data = np.ndarray((1,224,224,3),dtype=np.float32)
    data[0] = normalized
    pred = model.predict(data)
    index = np.argmax(pred)
    confidence = float(pred[0][index])
    predicted_class = class_names[index][2:].strip()
    return predicted_class, confidence

# =====================================================
# IMAGE UPLOAD + METADATA
# =====================================================
def upload_image(image, predicted_class):
    filename = f"{predicted_class}/{uuid.uuid4()}.jpg"
    buffer = io.BytesIO()
    image.save(buffer,format="JPEG")
    buffer.seek(0)
    supabase.storage.from_("fundbilder").upload(filename, buffer.getvalue(), {"content-type":"image/jpeg"})
    public_url = supabase.storage.from_("fundbilder").get_public_url(filename)
    return public_url

def save_metadata(image_url,predicted_class,confidence,tag):
    data = {
        "image_url":image_url,
        "predicted_class":predicted_class,
        "confidence":confidence,
        "tag":tag
    }
    supabase.table("fundstuecke").insert(data).execute()

def load_entries(class_filter=None, tag_filter=None):
    query = supabase.table("fundstuecke").select("*").order("created_at", desc=True)
    if class_filter and class_filter!="Alle":
        query = query.eq("predicted_class",class_filter)
    if tag_filter and tag_filter!="Alle":
        query = query.eq("tag",tag_filter)
    response = query.execute()
    return response.data

# =====================================================
# GALERIE
# =====================================================
if page=="Galerie":
    st.header("🖼 Fundstücke")
    class_filter = st.selectbox("Kategorie", ["Alle","Hoodie","Pants","Shoes"])
    tag_filter = st.selectbox("Farb Tag", ["Alle","rot","blau","grün","gelb","schwarz","weiß"])
    entries = load_entries(class_filter, tag_filter)
    if not entries:
        st.info("Keine Fundstücke vorhanden.")
    else:
        cols = st.columns(4)
        for i, entry in enumerate(entries):
            with cols[i%4]:
                st.markdown('<div class="thumbnail">', unsafe_allow_html=True)
                st.image(entry["image_url"],use_column_width=True)
                st.markdown(f"""
                    **{entry['predicted_class']}**  
                    Confidence: {round(entry['confidence']*100,2)} %  
                    Farbe: {entry['tag']}
                    """)
                st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# UPLOAD PAGE
# =====================================================
if page=="Upload":
    st.header("📦 Neues Fundstück")
    upload_tab, camera_tab = st.tabs(["📤 Datei hochladen","📷 Kamera"])
    image_file = None
    with upload_tab:
        uploaded_file = st.file_uploader("Bild auswählen", type=["jpg","jpeg","png"])
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
        tag = st.selectbox("Farb Tag auswählen", ["rot","blau","grün","gelb","schwarz","weiß"])
        if st.button("Speichern"):
            image_url = upload_image(image, predicted_class)
            save_metadata(image_url,predicted_class,confidence,tag)
            st.success("Fundstück gespeichert!")