import cv2
import numpy as np
import torch

def load_image(image_file, size=None):
    """Loads an image from a file-like object (Streamlit upload) or path."""
    if isinstance(image_file, str):
        img = cv2.imread(image_file)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    if size:
        img = cv2.resize(img, size)
    
    return img

def preprocess_image(img, size_w, size_h):
    """Resizes and normalizes image for the model."""
    img_resized = cv2.resize(img, (size_w, size_h))
    img_float = img_resized.astype(np.float32) / 255.0
    return img_float

def tensor_to_numpy(tensor):
    """Converts a tensor to a numpy array."""
    return tensor.detach().cpu().numpy()