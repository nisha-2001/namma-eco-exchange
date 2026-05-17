from fastapi import APIRouter
from app.schemas.schemas import ImageRequest, WasteClassificationResponse, MultiImageRequest, WasteClassificationBatchResponse
from app.services.image_processor import image_processor
import base64

router = APIRouter()

def strip_base64_prefix(data: str) -> str:
    """Remove the base64 prefix from the image data."""
    if "," in data:
        return data.split(",", 1)[1]
    return data

@router.post("/classify-waste/", response_model=WasteClassificationResponse)
async def classify_waste_endpoint(data: ImageRequest) -> WasteClassificationResponse:
    """Classify waste as organic or inorganic using CLIP zero-shot."""
    clean_base64 = strip_base64_prefix(data.image_base64)
    image_data = base64.b64decode(clean_base64)
    image = image_processor.prepare_image_for_analysis(image_data)
    result = image_processor.classify_waste(image)
    return result

@router.post("/classify-waste-batch/", response_model=WasteClassificationBatchResponse)
async def classify_waste_batch_endpoint(data: MultiImageRequest) -> WasteClassificationBatchResponse:
    """Classify multiple images in parallel and return a list of results with waste ratio and garbage rating."""
    import asyncio
    async def classify_one(b64_str: str):
        clean = strip_base64_prefix(b64_str)
        img_data = base64.b64decode(clean)
        img = image_processor.prepare_image_for_analysis(img_data)
        return image_processor.classify_waste(img)

    tasks = [classify_one(b64) for b64 in data.images]
    results = await asyncio.gather(*tasks)

    # Calculate waste ratio
    organic_count = sum(1 for result in results if result["classification"] == "organic")
    waste_ratio = organic_count / len(data.images) if data.images else 0

    # Calculate garbage rating
    garbage_rating = organic_count / len(data.images) if data.images else 0

    return {
        "results": results,
        "waste_ratio": waste_ratio,
        "garbageRating": garbage_rating
    }