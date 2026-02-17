import streamlit as st
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image, ImageOps

# Load model
model = load_model("keras_model.h5", compile=False)
class_names = open("labels.txt", "r").readlines()

st.title("Teachable Machine Classifier")
st.write("Take a photo of a hand, head, or pencil")

# Streamlit webcam
image_file = st.camera_input("Take a picture")

if image_file is not None:

    image = Image.open(image_file).convert("RGB")

    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)

    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1

    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array

    prediction = model.predict(data)
    index = np.argmax(prediction)
    confidence_score = prediction[0][index]

    st.subheader("Prediction")
    st.write(class_names[index][2:])
    st.write(f"Confidence: {round(confidence_score * 100, 2)}%")

    st.subheader("All Probabilities")
    for i, label in enumerate(class_names):
        st.write(f"{label[2:].strip()}: {prediction[0][i] * 100:.2f}%")