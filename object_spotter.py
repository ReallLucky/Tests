import streamlit as st
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image, ImageOps
from supabase import create_client
import uuid
import io
import requests
# =====================================================
# SEND EMAIL STUB
# =====================================================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =====================================================
# SQL ALTER STATEMENT
# =====================================================
# -- Füge neue Felder zur Tabelle fundstuecke hinzu:
# ALTER TABLE fundstuecke
#   ADD COLUMN kategorie TEXT,
#   ADD COLUMN status TEXT,
#   ADD COLUMN description TEXT,
#   ADD COLUMN email TEXT;

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(page_title="Lost&Found", layout="wide")

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

if "screen_width" not in st.session_state:
    st.session_state.screen_width = 1024  # default fallback

# sync page from URL
params = st.query_params
if "page" in params:
    st.session_state.page = params["page"]

def send_email(entry):
    recipient = entry.get("email", "")
    if not recipient:
        st.warning("Keine Email-Adresse angegeben. Email wird nicht gesendet.")
        return

    # Email credentials from Streamlit secrets
    sender_email = st.secrets["email"]["address"]
    sender_password = st.secrets["email"]["password"]
    smtp_server = st.secrets["email"].get("smtp_server", "smtp.gmail.com")
    smtp_port = int(st.secrets["email"].get("smtp_port", 587))

    # Prepare email content
    subject = "Lost&Found: Ihr Fundstück wurde gefunden!"
    image_url = entry.get("image_url", "")
    message_text = (
        "Hallo,\n\n"
        "Ihr Fundstück wurde auf Lost&Found gefunden! "
        "Hier ist der Link zum Bild:\n"
        f"{image_url}\n\n"
        "Falls Sie noch Fragen haben, antworten Sie bitte auf diese Email.\n\n"
        "Viele Grüße,\nDas Lost&Found Team"
    )

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(message_text, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
        st.success(f"Email an {recipient} gesendet.")
    except Exception as e:
        st.error(f"Fehler beim Senden der Email: {e}")

# =====================================================
# HELPER FUNCTION TO DETERMINE TOPBAR USAGE
# =====================================================
def should_use_topbar():
    # Approximate threshold for screen width to switch layout
    threshold_width = 500
    # Use stored screen width if available
    width = st.session_state.screen_width
    if width < threshold_width:
        return True
    return False

# =====================================================
# STYLE
# =====================================================

# Base CSS
st.markdown("""
<style>
/* HIDE STREAMLIT DEFAULT UI */
header {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stDecoration"] {display: none;}

/* TOPBAR (mobile / portrait) */

.topbar{
position:fixed;
top:0;
left:0;
width:100%;
height:60px;
background:rgba(20,20,20,0.9);
backdrop-filter:blur(20px);
display:none;
align-items:center;
justify-content:space-around;
border-bottom:1px solid #222;
z-index:999;
}

.topbar a{
color:white !important;
text-decoration:none !important;
font-weight:700;
font-size:18px;
}

[data-testid="stAppViewContainer"]{
    background: radial-gradient(circle at bottom,#000033 0%,#000000 60%);
    background-attachment: fixed;
}

/* RESPONSIVE SWITCH */

@media (max-aspect-ratio: 1/1){

.sidebar{
display:none;
}

.topbar{
display:flex;
}

.main .block-container{
margin-left:0 !important;
margin-top:70px;
}

}

/* SIDEBAR */

.sidebar{
position:fixed;
top:0;
left:0;
height:100vh;
width:70px;
background:rgba(20,20,20,0.85);
backdrop-filter:blur(20px);
transition:0.3s;
overflow:hidden;
border-right:1px solid #222;
z-index:999;
padding-top:20px;
}

.sidebar:hover{
width:210px;
}

.sidebar-item{
display:flex;
align-items:center;
gap:14px;
color:white !important;
text-decoration:none !important;
font-size:16px;
font-weight:700;
padding:14px 18px;
border-radius:10px;
margin:4px 8px;
transition:0.2s;
}

.sidebar-item:link,
.sidebar-item:visited{
color:white !important;
text-decoration:none !important;
}

.sidebar-item:hover{
background:#1f1f1f;
}

.sidebar-icon{
font-size:20px;
width:28px;
text-align:center;
}

.sidebar-text{
opacity:0;
white-space:nowrap;
transition:0.2s;
}

.sidebar:hover .sidebar-text{
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
# CONDITIONAL STYLE FOR TOPBAR / SIDEBAR
# =====================================================

if should_use_topbar():
    st.markdown("""
    <style>
    .topbar{
        display:flex !important;
    }
    .sidebar{
        display:none !important;
    }
    .main .block-container{
        margin-left:0 !important;
        margin-top:70px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================================
# CUSTOM SIDEBAR / TOPBAR
# =====================================================

st.markdown("""
<div class="topbar">
<a href="?page=Galerie" target="_self">🏠</a>
<a href="?page=Upload" target="_self">📦</a>
<a href="?page=Admin" target="_self">🔐</a>
</div>
<div class="sidebar">

<a class="sidebar-item" href="?page=Galerie" target="_self">
<span class="sidebar-icon">🏠</span>
<span class="sidebar-text">Galerie</span>
</a>

<a class="sidebar-item" href="?page=Upload" target="_self">
<span class="sidebar-icon">📦</span>
<span class="sidebar-text">Neuer Fund</span>
</a>

<a class="sidebar-item" href="?page=Admin" target="_self">
<span class="sidebar-icon">🔐</span>
<span class="sidebar-text">Admin</span>
</a>

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

def save_metadata(url, predicted_class, confidence, tag, kategorie, status, description, email):
    data = {
        "image_url": url,
        "predicted_class": predicted_class,
        "confidence": confidence,
        "tag": tag,
        "kategorie": kategorie,
        "status": status,
        "description": description,
        "email": email
    }
    supabase.table("fundstuecke").insert(data).execute()

# =====================================================
# LOAD ENTRIES
# =====================================================

def load_entries(class_filter=None,tag_filter=None,status_filter=None):

    query=supabase.table("fundstuecke").select("*").order("created_at",desc=True)

    if class_filter and class_filter!="Alle":
        query=query.eq("predicted_class",class_filter)

    if tag_filter and tag_filter!="Alle":
        query=query.eq("tag",tag_filter)

    if status_filter and status_filter!="Alle":
        query=query.eq("status",status_filter)

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

def render_gallery(entries, admin=False):
    cols = st.columns(4)
    for i, entry in enumerate(entries):
        with cols[i % 4]:
            try:
                response = requests.get(entry["image_url"])
                image = Image.open(io.BytesIO(response.content))
                image = square_crop(image)
                st.image(image, width="stretch")
            except:
                st.warning("Bild konnte nicht geladen werden")

            # Compose tags
            farbe = entry.get("tag", "-")
            status = entry.get("status", "-")
            predicted_class = entry.get("predicted_class", "-")
            tags = f"**Kategorie:** {predicted_class} &nbsp; **Farbe:** {farbe} &nbsp; **Status:** {status}"

            # Show expander for details with all info inside
            with st.expander("Details anzeigen"):
                st.markdown(tags, unsafe_allow_html=True)
                desc = entry.get("description", "")
                mail = entry.get("email", "")
                st.markdown(f"**Beschreibung:**<br>{desc}", unsafe_allow_html=True)
                st.markdown(f"**Email:** {mail}", unsafe_allow_html=True)

                if admin:
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if entry.get("status") == "Missing":
                            if st.button("✉️ Email senden", key=f"email_{entry['id']}"):
                                send_email(entry)
                    with c2:
                        if st.button("🗑 Löschen", key=f"del_{entry['id']}"):
                            delete_entry(entry)
                            st.rerun()
                    # Style delete button text as red
                    st.markdown("""
                        <style>
                        button[kind="secondary"] > div > span:has-text("🗑 Löschen") {
                            color: red !important;
                        }
                        </style>
                    """, unsafe_allow_html=True)

# =====================================================
# PAGE ROUTER
# =====================================================

page=st.session_state.page

# =====================================================
# GALERIE
# =====================================================

if page=="Galerie":

    st.title("👋 Willkommen bei Lost&Found")

    st.write("""
    **Lost&Found hilft verlorene Kleidung wiederzufinden**

    1️⃣ Kleidung wird hochgeladen  
    2️⃣ KI erkennt Kategorie  
    3️⃣ Farbtag wird hinzugefügt  
    4️⃣ Besitzer können ihre Kleidung wiederfinden
    """)

    st.divider()

    status_filter, class_filter, tag_filter = st.columns(3)

    with status_filter:
        status_filter_val = st.selectbox("Status", ["Alle", "Found", "Missing"])

    with class_filter:
        class_filter_val = st.selectbox("Kategorie", ["Alle", "Hoodie", "Hose", "Schuhe"])

    with tag_filter:
        tag_filter_val = st.selectbox("Farb Tag", ["Alle", "rot", "blau", "grün", "gelb", "schwarz", "weiß"])

    entries=load_entries(class_filter_val, tag_filter_val, status_filter_val)

    entries=entries[:st.session_state.batch_size]

    render_gallery(entries)

    if len(load_entries())>st.session_state.batch_size:

        if st.button("Mehr laden"):

            st.session_state.batch_size+=12
            st.rerun()

# =====================================================
# UPLOAD
# =====================================================

if page == "Upload":
    st.title("📦 Neues Fundstück")
    tab1, tab2 = st.tabs(["Upload", "Kamera"])
    image_file = None
    with tab1:
        uploaded = st.file_uploader("Bild auswählen", type=["jpg", "jpeg", "png"])
        if uploaded:
            image_file = uploaded
    with tab2:
        # Responsive camera input: center and widen on desktop, default on mobile/narrow screens
        if not should_use_topbar():
            # Desktop/wide: center camera in wide column
            cam_left, cam_center, cam_right = st.columns([1, 2, 1])
            with cam_center:
                camera = st.camera_input("Foto aufnehmen")
        else:
            # Mobile/narrow: default
            camera = st.camera_input("Foto aufnehmen")
        if camera:
            image_file = camera

    if image_file:
        image = Image.open(image_file).convert("RGB")
        st.image(image, width="stretch")
        predicted_class, confidence = classify_image(image)
        st.subheader("🤖 KI Ergebnis")
        st.write("Klasse:", predicted_class)
        st.progress(confidence)

        tag = st.selectbox("Farbe", ["rot", "blau", "grün", "gelb", "schwarz", "weiß"])
        status = st.selectbox("Status", ["Found", "Missing"])
        description = st.text_area("Beschreibung", max_chars=500)
        email = st.text_input("Email (optional)")

        if st.button("Speichern"):
            url = upload_image(image, predicted_class)
            save_metadata(
                url, predicted_class, confidence, tag, predicted_class, status, description, email
            )
            st.success("Fundstück gespeichert!")

# =====================================================
# ADMIN
# =====================================================

header_left, header_right = st.columns([1,0.2])

if page=="Admin":

    with header_left:
        st.title("🔐 Admin")

    with header_right:
        if st.session_state.admin_logged_in:
            if st.button("Logout"):
                st.session_state.admin_logged_in=False
                st.rerun()

    if not st.session_state.admin_logged_in:

        password=st.text_input("Admin Passwort",type="password")

        if st.button("Login"):

            if password==ADMIN_PASSWORD:

                st.session_state.admin_logged_in=True
                st.rerun()

            else:

                st.error("Falsches Passwort")

    else:
        # Add filters similar to Galerie page
        status_filter_col, class_filter_col, tag_filter_col = st.columns(3)

        with status_filter_col:
            status_filter_val = st.selectbox("Status", ["Alle", "Found", "Missing"], key="admin_status_filter")

        with class_filter_col:
            class_filter_val = st.selectbox("Kategorie", ["Alle", "Hoodie", "Hose", "Schuhe"], key="admin_class_filter")

        with tag_filter_col:
            tag_filter_val = st.selectbox("Farb Tag", ["Alle", "rot", "blau", "grün", "gelb", "schwarz", "weiß"], key="admin_tag_filter")

        entries = load_entries(class_filter_val, tag_filter_val, status_filter_val)
        render_gallery(entries, admin=True)

