from fastapi import FastAPI, HTTPException, Request, status, Body, Depends
from pydantic import BaseModel, Field, ValidationError
from fastapi.responses import JSONResponse
from typing import Optional
from PIL import Image, UnidentifiedImageError
import base64
import io
import logging
import time
import os

"""
Since it is a hiring task, I also save the incoming/outgoing base64 images into the log data too. Normally I can save it as image or write them in a table. 

Also returned the correct format to user if a user sends an unprocessable entity.

I completed this task in an hour so, there can be multiple things to be done here but that operations could need complex error handling operations too. So I kept it basic to show my ability to develop this kind of API's.
"""

app = FastAPI()

log_directory = "/tmp/logs"
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{log_directory}/app.log", mode='a'),
        logging.StreamHandler()
    ]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    logging.info("Health check endpoint was called.")
    return {"status": "ok"}

class TransformRequest(BaseModel):
    image: str
    transformation_type: str  # grayscale, rotate, resize
    rotation_angle: Optional[int] = None  # Used if transformation_type is 'rotate'
    width: Optional[int] = Field(None, ge=0)  # Used if transformation_type is 'resize', must be non-negative
    height: Optional[int] = Field(None, ge=0)  # Used if transformation_type is 'resize', must be non-negative

class TransformResponse(BaseModel):
    transformed_image: str

def validate_input(data: dict = Body(...)):
    required_fields = ["image", "transformation_type"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        correct_format = {
            "image": "<Base64-encoded-image>",
            "transformation_type": "<grayscale|rotate|resize>",
            "rotation_angle": "<integer>",
            "width": "<positive integer>",
            "height": "<positive integer>"
        }
        response = {
            "error": f"Missing required fields: {missing_fields}",
            "correct_format": correct_format
        }
        logging.error(f"Returning to user: {response}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=response
        )
    
    # Additional checks for resize and rotate transformations
    if data["transformation_type"] == "resize" and (data.get("width") is None or data.get("height") is None):
        response = {
            "error": "Width and height must be provided for resize transformation.",
            "correct_format": {
                "image": "<Base64-encoded-image>",
                "transformation_type": "resize",
                "width": "<positive integer>",
                "height": "<positive integer>"
            }
        }
        logging.error(f"Returning to user: {response}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=response)
    
    if data["transformation_type"] == "rotate" and data.get("rotation_angle") is None:
        response = {
            "error": "Rotation angle must be provided for rotate transformation.",
            "correct_format": {
                "image": "<Base64-encoded-image>",
                "transformation_type": "rotate",
                "rotation_angle": "<integer>"
            }
        }
        logging.error(f"Returning to user: {response}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=response)
    
    return data

def process_image(image: Image.Image, transformation_type: str, rotation_angle: int = 0, width: int = 0, height: int = 0) -> Image.Image:
    if transformation_type == "grayscale":
        return image.convert("L")
    elif transformation_type == "rotate":
        return image.rotate(rotation_angle, expand=True)
    elif transformation_type == "resize":
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive integers for resizing.")
        return image.resize((width, height))
    else:
        raise ValueError("Invalid transformation type")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logging.info(f"Incoming request: {request.method} {request.url}")
    logging.info(f"Request body: {await request.body()}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logging.info(f"Request processed in {process_time:.2f} seconds")
    
    if response.status_code == 200:
        logging.info("Operation was successful.")
    else:
        logging.error(f"Operation failed with status code {response.status_code}.")
    
    return response

@app.post("/transform", response_model=TransformResponse)
async def transform_image(request_data: dict = Depends(validate_input)):
    try:
        logging.info(f"Transformation requested: {request_data['transformation_type']}")
        
        # Log before decoding
        logging.info("Decoding base64 image")
        image_data = base64.b64decode(request_data["image"])
        logging.info("Base64 image decoded successfully")
        
        # Log before opening the image
        try:
            logging.info("Opening image from decoded data")
            image = Image.open(io.BytesIO(image_data))
            logging.info("Image opened successfully")
        except Exception as e:
            response = {"detail": "Invalid image file. Ensure the image is a valid Base64 encoded string representing an image."}
            logging.error(f"Invalid image file: {str(e)}. Returning to user: {response}")
            raise HTTPException(status_code=400, detail=response)

        # Log before processing the image
        logging.info("Processing image transformation")
        transformed_image = process_image(
            image,
            request_data["transformation_type"],
            request_data.get("rotation_angle", 0),
            request_data.get("width", 0),
            request_data.get("height", 0)
        )
        logging.info("Image transformation completed")

        # Log before encoding the image back to base64
        buffered = io.BytesIO()
        transformed_image.save(buffered, format="JPEG")
        transformed_image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        logging.info("Transformed image encoded to base64 successfully")

        response = TransformResponse(transformed_image=transformed_image_base64)
        logging.info(f"Returning transformed image to user")
        return response
    
    except UnidentifiedImageError:
        response = {"detail": "Invalid image provided. Ensure the image is a valid Base64 encoded string representing an image."}
        logging.error(f"Invalid image provided. Returning to user: {response}")
        raise HTTPException(status_code=400, detail=response)
    except ValueError as e:
        response = {"detail": f"Invalid transformation type or parameter: {str(e)}."}
        logging.error(f"Invalid transformation type or parameter. Returning to user: {response}")
        raise HTTPException(status_code=400, detail=response)
    except Exception as e:
        response = {"detail": f"Internal server error: {str(e)}"}
        logging.error(f"Error during transformation: {str(e)}. Returning to user: {response}")
        raise HTTPException(status_code=500, detail=response)