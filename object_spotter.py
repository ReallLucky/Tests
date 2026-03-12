import streamlit as st
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image, ImageOps
from supabase import create_client
import uuid
import io
import requests

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(page_title="FundTube", layout="wide")

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
ADMIN_PASSWORD = st.secrets["admin_password"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# SESSION STATE
# =====================================================

if "page" not in st.session_state:
    st.session_state.page = "Galerie"

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "batch_size" not in st.session_state:
    st.session_state.batch_size = 12

# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>

[data-testid="stAppViewContainer"]{
background: radial-gradient(circle at bottom,#000033 0%,#000000 60%);
background-attachment:fixed;
}

/* SIDEBAR */

.sidebar{
position:fixed;
top:0;
left:0;
height:100vh;
width:70px;
background:rgba(20,20,20,0.85);
backdrop-filter: blur(20px);
transition:0.3s;
overflow:hidden;
border-right:1px solid #222;
z-index:999;
padding-top:20px;
}

.sidebar:hover{
width:200px;
}

.sidebar-nav{
display:flex;
flex-direction:column;
}

.sidebar-item{
display:flex;
align-items:center;
color:white;
background:none;
border:none;
width:100%;
padding:16px;
font-size:18px;
cursor:pointer;
text-align:left;
}

.sidebar-item:hover{
background:#1f1f1f;
}

.sidebar-icon{
font-size:20px;
width:24px;
}

.sidebar-label{
margin-left:12px;
opacity:0;
transition:0.2s;
white-space:nowrap;
}

.sidebar:hover .sidebar-label{
opacity:1;
}

/* CONTENT SHIFT */

.main .block-container{
margin-left:90px;
}

/* GALLERY */

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

/* CONFIDENCE BAR */

.conf-bar{
height:8px;
background:#333;
border-radius:4px;
overflow:hidden;
margin-top:5px;
}

.conf-fill{
height:8px;
background:linear-gradient(90deg,#00c6ff,#0072ff);
}

img{
border-radius:10px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================

st.markdown("""
<div class="sidebar">

<div class="sidebar-nav">

<a class="sidebar-item" href="?page=Galerie">
<span class="sidebar-icon">🏠</span>
<span class="sidebar-label">Galerie</span>
</a>

<a class="sidebar-item" href="?page=Upload">
<span class="sidebar-icon">📦</span>
<span class="sidebar-label">Neuer Fund</span>
</a>

<a class="sidebar-item" href="?page=Admin">
<span class="sidebar-icon">🔐</span>
<span class="sidebar-label">Admin</span>
</a>

</div>

</div>
""", unsafe_allow_html=True)

# =====================================================
# LOAD MODEL
# =====================================================

@st.cache_resource
def load_tm_model():
    model = load_model("keras_model.h5", compile=False)
    class_names = open("labels.txt").readlines()
    return model, class_names

model, class_names = load_tm_model()

# =====================================================
# IMAGE HELPERS
# =====================================================

def square_crop(image):
    w,h=image.size
    m=min(w,h)
    left=(w-m)//2
    top=(h-m)//2
    right=(w+m)//2
    bottom=(h+m)//2
    return image.crop((left,top,right,bottom))

# =====================================================
# CLASSIFY IMAGE
# =====================================================

def classify_image(image):

    size=(224,224)

    image = ImageOps.fit(image,size,Image.Resampling.LANCZOS)

    image_array=np.asarray(image)

    normalized=(image_array.astype(np.float32)/127.5)-1

    data=np.ndarray((1,224,224,3),dtype=np.float32)

    data[0]=normalized

    prediction=model.predict(data)

    index=np.argmax(prediction)

    confidence=float(prediction[0][index])

    predicted_class=class_names[index][2:].strip()

    return predicted_class,confidence

# =====================================================
# STORAGE
# =====================================================

def upload_image(image,predicted_class):

    filename=f"{predicted_class}/{uuid.uuid4()}.jpg"

    buffer=io.BytesIO()

    image.save(buffer,format="JPEG")

    buffer.seek(0)

    supabase.storage.from_("fundbilder").upload(
        filename,
        buffer.getvalue(),
        {"content-type":"image/jpeg"}
    )

    url=supabase.storage.from_("fundbilder").get_public_url(filename)

    return url

# =====================================================
# SAVE METADATA
# =====================================================

def save_metadata(url,predicted_class,confidence,tag):

    data={
        "image_url":url,
        "predicted_class":predicted_class,
        "confidence":confidence,
        "tag":tag
    }

    supabase.table("fundstuecke").insert(data).execute()

# =====================================================
# LOAD ENTRIES
# =====================================================

def load_entries(class_filter=None,tag_filter=None):

    query=supabase.table("fundstuecke").select("*").order("created_at",desc=True)

    if class_filter and class_filter!="Alle":
        query=query.eq("predicted_class",class_filter)

    if tag_filter and tag_filter!="Alle":
        query=query.eq("tag",tag_filter)

    res=query.execute()

    return res.data

# =====================================================
# DELETE ENTRY
# =====================================================

def delete_entry(entry):

    image_url=entry["image_url"]

    path=image_url.split("/fundbilder/")[1]

    supabase.storage.from_("fundbilder").remove([path])

    supabase.table("fundstuecke").delete().eq("id",entry["id"]).execute()

# =====================================================
# GALLERY RENDER
# =====================================================

def render_gallery(entries,admin=False):

    cols=st.columns(4)

    for i,entry in enumerate(entries):

        with cols[i%4]:

            try:

                response=requests.get(entry["image_url"])
                image=Image.open(io.BytesIO(response.content))

                image=square_crop(image)

                st.image(image,use_container_width=True)

            except:

                st.warning("Bild konnte nicht geladen werden")

            conf=int(entry["confidence"]*100)

            st.markdown(f"**{entry['predicted_class']}**")

            st.markdown(f"""
            <div class="conf-bar">
            <div class="conf-fill" style="width:{conf}%"></div>
            </div>
            """,unsafe_allow_html=True)

            st.write(conf,"%")

            st.write("Farbe:",entry["tag"])

            if admin:

                if st.button("🗑 Löschen",key=f"del_{entry['id']}"):

                    delete_entry(entry)
                    st.rerun()

# =====================================================
# QUERY PARAM ROUTER
# =====================================================

params = st.query_params

if "page" in params:
    st.session_state.page = params["page"]

# =====================================================
# PAGE ROUTER
# =====================================================

page=st.session_state.page

# =====================================================
# GALERIE
# =====================================================

if page=="Galerie":

    st.title("👋 Willkommen bei FundTube")

    st.write("""
    **FundTube hilft verlorene Kleidung wiederzufinden**

    1️⃣ Kleidung wird hochgeladen  
    2️⃣ KI erkennt Kategorie  
    3️⃣ Farbtag wird hinzugefügt  
    4️⃣ Besitzer können ihre Kleidung wiederfinden
    """)

    st.divider()

    class_filter=st.selectbox("Kategorie",["Alle","Hoodie","Pants","Shoes"])

    tag_filter=st.selectbox("Farb Tag",["Alle","rot","blau","grün","gelb","schwarz","weiß"])

    entries=load_entries(class_filter,tag_filter)

    entries=entries[:st.session_state.batch_size]

    render_gallery(entries)

    if len(load_entries())>st.session_state.batch_size:

        if st.button("Mehr laden"):

            st.session_state.batch_size+=12
            st.rerun()

# =====================================================
# UPLOAD
# =====================================================

if page=="Upload":

    st.title("📦 Neues Fundstück")

    tab1,tab2=st.tabs(["Upload","Kamera"])

    image_file=None

    with tab1:

        uploaded=st.file_uploader("Bild auswählen",type=["jpg","jpeg","png"])

        if uploaded:
            image_file=uploaded

    with tab2:

        camera=st.camera_input("Foto aufnehmen")

        if camera:
            image_file=camera

    if image_file:

        image=Image.open(image_file).convert("RGB")

        st.image(image,use_container_width=True)

        predicted_class,confidence=classify_image(image)

        st.subheader("🤖 KI Ergebnis")

        st.write("Klasse:",predicted_class)

        st.progress(confidence)

        tag=st.selectbox("Farb Tag",["rot","blau","grün","gelb","schwarz","weiß"])

        if st.button("Speichern"):

            url=upload_image(image,predicted_class)

            save_metadata(url,predicted_class,confidence,tag)

            st.success("Fundstück gespeichert!")

# =====================================================
# ADMIN
# =====================================================

if page=="Admin":

    st.title("🔐 Admin")

    if not st.session_state.admin_logged_in:

        password=st.text_input("Admin Passwort",type="password")

        if st.button("Login"):

            if password==ADMIN_PASSWORD:

                st.session_state.admin_logged_in=True
                st.rerun()

            else:

                st.error("Falsches Passwort")

    else:

        if st.button("Logout"):

            st.session_state.admin_logged_in=False
            st.rerun()

        entries=load_entries()

        render_gallery(entries,admin=True)