import streamlit as st
import cv2
import numpy as np
from keras.models import load_model
from PIL import Image, ImageOps

# Disable scientific notation
np.set_printoptions(suppress=True)

# Load the model
model = load_model("keras_Model.h5", compile=False)

# Load labels
class_names = open("labels.txt", "r").readlines()

st.title("🧠 Teachable Machine Live Classifier")
st.write("Show your **hand**, **head**, or **pencil** to the webcam.")

# Start/Stop checkbox
run = st.checkbox("Start Webcam")

# Create placeholder for video
FRAME_WINDOW = st.image([])

# Open webcam
camera = cv2.VideoCapture(0)

while run:
    ret, frame = camera.read()
    if not ret:
        st.error("Webcam not detected.")
        break

    # Convert frame (OpenCV uses BGR)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb).convert("RGB")

    # Resize and crop exactly like Teachable Machines code
    size = (224, 224)
    image = ImageOps.fit(pil_image, size, Image.Resampling.LANCZOS)

    # Convert to numpy array
    image_array = np.asarray(image)

    # Normalize image
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1

    # Create data array
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array

    # Predict
    prediction = model.predict(data)
    index = np.argmax(prediction)
    class_name = class_names[index][2:].strip()
    confidence_score = prediction[0][index]

    # Show webcam feed
    FRAME_WINDOW.image(frame_rgb)

    # Display predictions
    st.subheader("Prediction:")
    st.write(f"### {class_name}")
    st.write(f"Confidence: {round(confidence_score * 100, 2)} %")

    # Show all class probabilities
    st.subheader("All Class Probabilities:")
    for i, label in enumerate(class_names):
        label_name = label[2:].strip()
        prob = prediction[0][i] * 100
        st.write(f"{label_name}: {prob:.2f}%")

camera.release()