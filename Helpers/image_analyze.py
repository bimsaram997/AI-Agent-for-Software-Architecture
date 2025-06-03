import os
import torch
import open_clip
from PIL import Image

# Load model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess, _ = open_clip.create_model_and_transforms("ViT-B/32", pretrained="openai")
tokenizer = open_clip.get_tokenizer("ViT-B-32")
# Folder containing images
folder_path = "spacebased"

# Define architecture patterns
architecture_patterns = [
    "Space-Based Architecture"
]

# Encode text inputs
text_inputs = tokenizer(architecture_patterns).to(device)

# Process images
for filename in os.listdir(folder_path):
    if filename.lower().endswith((".jpg", ".png", ".jpeg")):
        image_path = os.path.join(folder_path, filename)

        try:
            image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)

            with torch.no_grad():
                image_features = model.encode_image(image)
                text_features = model.encode_text(text_inputs)
                similarity = (image_features @ text_features.T).softmax(dim=-1)

            best_match_idx = similarity.argmax().item()
            new_name = architecture_patterns[best_match_idx].replace(" ", "_") + ".jpg"
            new_path = os.path.join(folder_path, new_name)

            # ✅ Ensure unique file name (prevents overwriting)
            counter = 1
            base_name, ext = os.path.splitext(new_name)
            while os.path.exists(new_path):
                new_path = os.path.join(folder_path, f"{base_name}_{counter}{ext}")
                counter += 1

            os.rename(image_path, new_path)
            print(f"✅ Renamed: {filename} → {os.path.basename(new_path)}")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

print("🎉 Renaming complete!")
