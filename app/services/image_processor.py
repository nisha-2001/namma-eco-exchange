"""
Image processing utilities and basic analysis functions.

This module contains general image processing functions and 
basic analysis capabilities that support the main application.
"""

from typing import Dict, Any, List
import torch
from PIL import Image
from io import BytesIO
from .config import OBJECT_DETECTION_THRESHOLD, MAX_IMAGE_SIZE, MIN_IMAGE_SIZE
from transformers import CLIPProcessor, CLIPModel, BlipProcessor, BlipForConditionalGeneration

# Initialize models and processors
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def strip_base64_prefix(base64_string: str) -> str:
    """
    Strip data URI prefix from base64 string if present.

    Handles formats like:
    - data:image/jpeg;base64,<data>
    - data:image/png;base64,<data>
    - data:image/webp;base64,<data>

    Args:
        base64_string: Base64 string (with or without data URI prefix)

    Returns:
        Clean base64 string without prefix
    """
    # Check if string starts with data URI prefix
    if base64_string.startswith('data:'):
        # Find the comma that separates the prefix from the data
        comma_index = base64_string.find(',')
        if comma_index != -1:
            return base64_string[comma_index + 1:]

    return base64_string

class ImageProcessor:
    """General image processing and analysis service."""

    def __init__(self, clip_processor, clip_model, blip_processor, blip_model, device):
        """Initialize the processor with AI models."""
        self.clip_processor = clip_processor
        self.clip_model = clip_model
        self.blip_processor = blip_processor
        self.blip_model = blip_model
        self.device = device

    def basic_image_caption(self, image: Image.Image) -> str:
        """Generate a basic caption for an image using BLIP (optimized for speed)."""
        inputs = self.blip_processor(image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            generated_ids = self.blip_model.generate(
                **inputs, 
                max_length=30,
                num_beams=1,
                do_sample=False,
                early_stopping=True
            )
            caption = self.blip_processor.decode(generated_ids[0], skip_special_tokens=True)

        return caption

    def detailed_product_caption(self, image: Image.Image) -> str:
        """Generate a detailed product description using BLIP with better parameters."""
        inputs = self.blip_processor(image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            generated_ids = self.blip_model.generate(
                **inputs, 
                max_length=50,
                min_length=10,
                num_beams=3,
                no_repeat_ngram_size=2,
                length_penalty=1.0,
                early_stopping=True
            )
            caption = self.blip_processor.decode(generated_ids[0], skip_special_tokens=True)

        return caption

    def detect_custom_objects(self, image: Image.Image, object_list: List[str], threshold: float = OBJECT_DETECTION_THRESHOLD) -> List[Dict[str, Any]]:
        """Detect custom objects in an image using CLIP zero-shot classification."""
        # Prepare queries
        object_queries = [f"a photo of a {obj}" for obj in object_list]

        inputs = self.clip_processor(text=object_queries, images=image, return_tensors="pt", padding=True).to(self.device)

        with torch.no_grad():
            outputs = self.clip_model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)

        # Filter results with confidence > threshold
        detected_objects = []

        for i, prob in enumerate(probs[0]):
            if prob > threshold:
                detected_objects.append({
                    "object": object_list[i],
                    "confidence": float(prob),
                    "likelihood": "high" if prob > 0.5 else "medium" if prob > 0.25 else "low"
                })

        # Sort by confidence
        detected_objects.sort(key=lambda x: x["confidence"], reverse=True)

        return detected_objects

    def classify_waste(self, image: Image.Image) -> Dict[str, Any]:
        """Classify waste type (organic vs inorganic) using CLIP zero-shot.
        Returns a dict with 'classification' and 'confidence'.
        """
        categories = ["organic", "inorganic"]
        # Prepare zero-shot text queries
        queries = [f"a photo of {c} waste" for c in categories]
        inputs = self.clip_processor(text=queries, images=image, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.clip_model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)[0]
        max_idx = int(probs.argmax().item())
        return {
            "classification": categories[max_idx],
            "confidence": float(probs[max_idx])
        }

    def get_image_technical_info(self, image: Image.Image, image_data: bytes = None) -> Dict[str, Any]:
        """Extract technical information from an image."""
        width, height = image.size
        aspect_ratio = round(width / height, 2)

        # Basic color analysis
        colors = image.getcolors(maxcolors=256)
        if colors:
            dominant_color = max(colors, key=lambda item: item[0])
            color_info = {
                "dominant_color_count": dominant_color[0],
                "total_unique_colors": len(colors),
                "has_transparency": image.mode in ['RGBA', 'LA']
            }
        else:
            color_info = {"note": "Complex color palette"}

        technical_info = {
            "dimensions": f"{width}x{height}",
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "mode": image.mode,
            "format": image.format,
            "color_analysis": color_info
        }

        if image_data:
            technical_info["size_bytes"] = len(image_data)
            technical_info["size_kb"] = round(len(image_data) / 1024, 2)

        return technical_info

    def validate_image_for_ecommerce(self, image: Image.Image) -> Dict[str, Any]:
        """Validate if an image is suitable for e-commerce use."""
        width, height = image.size
        aspect_ratio = width / height

        validation_results = {
            "is_valid": True,
            "issues": [],
            "recommendations": [],
            "quality_score": 1.0
        }

        # Check dimensions
        if min(width, height) < 300:
            validation_results["issues"].append("Image resolution too low (minimum 300px)")
            validation_results["quality_score"] -= 0.3

        if max(width, height) > 4000:
            validation_results["issues"].append("Image resolution very high (consider compression)")
            validation_results["recommendations"].append("Optimize file size for web")

        # Check aspect ratio
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            validation_results["issues"].append("Unusual aspect ratio for product images")
            validation_results["quality_score"] -= 0.2

        # Check image mode
        if image.mode not in ['RGB', 'RGBA']:
            validation_results["issues"].append(f"Image mode '{image.mode}' may cause display issues")
            validation_results["recommendations"].append("Convert to RGB format")

        # General recommendations
        if 800 <= min(width, height) <= 1200:
            validation_results["recommendations"].append("Good resolution for web display")

        if 0.8 <= aspect_ratio <= 1.2:
            validation_results["recommendations"].append("Square format works well for product listings")

        # Final validation
        if validation_results["quality_score"] < 0.5:
            validation_results["is_valid"] = False

        validation_results["quality_score"] = max(0.0, validation_results["quality_score"])

        return validation_results

    def prepare_image_for_analysis(self, image_data: bytes) -> Image.Image:
        """Prepare and validate image data for analysis."""
        try:
            image = Image.open(BytesIO(image_data))

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Basic size validation
            width, height = image.size
            if width < MIN_IMAGE_SIZE[0] or height < MIN_IMAGE_SIZE[1]:
                raise ValueError(f"Image too small for analysis (minimum {MIN_IMAGE_SIZE[0]}x{MIN_IMAGE_SIZE[1]})")

            if width > MAX_IMAGE_SIZE[0] or height > MAX_IMAGE_SIZE[1]:
                # Resize very large images
                image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

            return image

        except Exception as e:
            raise ValueError(f"Invalid image data: {str(e)}")

    def extract_image_metadata(self, image: Image.Image) -> Dict[str, Any]:
        """Extract metadata from an image."""
        metadata = {
            "basic_info": {
                "size": image.size,
                "mode": image.mode,
                "format": image.format
            }
        }

        # Try to extract EXIF data
        try:
            if hasattr(image, '_getexif') and image._getexif():
                exif_data = image._getexif()
                if exif_data:
                    metadata["exif"] = {
                        "camera_make": exif_data.get(271, "Unknown"),
                        "camera_model": exif_data.get(272, "Unknown"),
                        "datetime": exif_data.get(306, "Unknown")
                    }
        except Exception:
            pass  # EXIF data not available or accessible

        return metadata

# Instantiate the image processor
image_processor = ImageProcessor(
    clip_processor=clip_processor,
    clip_model=clip_model,
    blip_processor=blip_processor,
    blip_model=blip_model,
    device="cpu"  # Change to "cuda" if using a GPU
)