import base64
import hashlib
import io
import os
from enum import Enum
from http import HTTPStatus

import qrcode
from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from pymongo import MongoClient
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer

app = FastAPI()

client: MongoClient = MongoClient(os.getenv("MONGO_DB_CONNECTION_STRING"))
db = client.qr_codes
collection = db.qr_codes


def hash_string(string_in: str):
    result = hashlib.md5(string_in.encode())
    return result.hexdigest()


class QRCodeDrawers(str, Enum):
    SQUARE_MODULE = "SQUARE_MODULE"
    GAPPED_SQUARE_MODULE = "GAPPED_SQUARE_MODULE"
    CIRCLE_MODULE = "CIRCLE_MODULE"
    ROUNDED_MODULE = "ROUNDED_MODULE"
    VERTICAL_BARS = "VERTICAL_BARS"
    HORIZONTAL_BARS = "HORIZONTAL_BARS"


class QRCodeMasks(str, Enum):
    SOLID_FILL = "SOLID_FILL"
    RADIAL_GRADIENT = "RADIAL_GRADIENT"
    SQUARE_GRADIENT = "SQUARE_GRADIENT"
    HORIZONTAL_GRADIENT = "HORIZONTAL_GRADIENT"
    VERTICAL_GRADIENT = "VERTICAL_GRADIENT"
    IMAGE_COLOR = "IMAGE_COLOR"


class Color(BaseModel):
    back: str
    primary: str | None
    secondary: str | None


class CreateQRCodeAPIRequest(BaseModel):
    target_url: str
    drawer: QRCodeDrawers | None
    mask: QRCodeMasks | None
    color: Color | None


class GetQRCodeAPIResponse(BaseModel):
    qr_link: str
    target_url: str
    scan_counter: int = 0
    identifier: str


class QRCodeEntryDB(BaseModel):
    qr_link: str
    target_url: str
    scan_counter: int = 0
    identifier: str
    image: str


@app.get("/health")
async def root():
    return {"health": "ok"}


@app.post("/qr", response_model=GetQRCodeAPIResponse)
async def create_qr_code(payload: CreateQRCodeAPIRequest, request: Request):
    img_name = hash_string(payload.target_url)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(f"{request.base_url}scan/{img_name}")
    img = qr.make_image(
        image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer()
    )
    img_file_path = f"./static/qrs/{img_name}.png"
    img_buffer = io.BytesIO()
    img.save(img_buffer, "PNG")
    img_buffer.seek(0)
    img.save(img_file_path, "PNG")
    qr_db_instance = QRCodeEntryDB(
        target_url=payload.target_url,
        qr_link=f"{request.url._url}/{img_name}/png",
        identifier=img_name,
        image=base64.b64encode(img_buffer.read()),
    )
    collection.insert_one(qr_db_instance.dict())
    return GetQRCodeAPIResponse(**qr_db_instance.dict())


@app.get("/qr/{identifier}")
async def get_qr_data(identifier: str, request: Request):
    document = collection.find_one({"identifier": identifier})
    if not document:
        return Response(status_code=HTTPStatus.NOT_FOUND)
    return GetQRCodeAPIResponse(**document)


@app.get("/qr/{identifier}/png")
async def get_qr_data(identifier: str, request: Request):
    document = collection.find_one({"identifier": identifier})
    if not document:
        return Response(status_code=HTTPStatus.NOT_FOUND)
    return StreamingResponse(
        io.BytesIO(base64.b64decode(document["image"])), media_type="image/png"
    )


@app.get("/scan/{identifier}")
async def redirect_scan(identifier: str, request: Request):
    document = collection.find_one({"identifier": identifier})
    if not document:
        return Response(status_code=HTTPStatus.NOT_FOUND)
    collection.update_one(
        {"identifier": identifier},
        {"$set": {"scan_counter": document["scan_counter"] + 1}},
    )
    return RedirectResponse(document["target_url"])
