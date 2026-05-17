"""
Configuration settings for the E-Commerce Image Analysis API
"""
 
# Model configurations
BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-base"
BLIP_ITM_MODEL_NAME = "Salesforce/blip-itm-large-coco"  # For image similarity
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
 
# Qdrant vector database settings
QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION_NAME = "products"
DEFAULT_TOP_K = 10
 
# Analysis thresholds
ECOMMERCE_FEATURE_THRESHOLD = 0.15
OBJECT_DETECTION_THRESHOLD = 0.1
PRODUCT_CONFIDENCE_THRESHOLD = 0.1
 
# Image processing settings
MAX_IMAGE_SIZE = (2000, 2000)
MIN_IMAGE_SIZE = (50, 50)
SUPPORTED_FORMATS = ["JPEG", "PNG", "JPG", "WEBP"]
 
# E-commerce categories
ECOMMERCE_CATEGORIES = [
    "clothing and apparel",
    "shoes and footwear",
    "electronics and gadgets",
    "home and furniture",
    "beauty and cosmetics",
    "jewelry and accessories",
    "books and media",
    "toys and games",
    "sports equipment",
    "food and beverages",
    "automotive parts",
    "health products",
    "garden and outdoor",
    "office supplies",
    "baby and kids products",
    "pet supplies",
    "tools and hardware"
]
 
# E-commerce features to detect
ECOMMERCE_FEATURES = [
    "price tag or price label",
    "barcode",
    "QR code",
    "product packaging",
    "brand logo",
    "size label",
    "product rating stars",
    "discount badge",
    "shopping cart icon",
    "wishlist icon",
    "product gallery",
    "color swatches",
    "size chart",
    "product review",
    "shipping information",
    "product comparison"
]
 
# Default objects for detection
DEFAULT_ECOMMERCE_OBJECTS = [
    "clothing",
    "electronics",
    "shoes",
    "accessories",
    "furniture",
    "beauty products",
    "brand logo",
    "price tag",
    "rating stars",
    "discount badge",
    "barcode",
    "QR code"
]
 