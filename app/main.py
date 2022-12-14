import base64
import hashlib
import io
import os
from enum import Enum
from http import HTTPStatus
from datetime import datetime
import json
import qrcode
from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel as PydanticBaseModel, Field, root_validator
from pymongo import MongoClient
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles import moduledrawers
from qrcode.image.styles import colormasks
from typing import Optional

from fastapi.middleware.cors import CORSMiddleware
import logging

from functools import partial
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://qr-code-generator-3p8.pages.dev", 
        "http://qr-code-generator-3p8.pages.dev"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger("pymongo").setLevel(logging.DEBUG)



client: MongoClient = MongoClient(os.getenv("MONGO_DB_CONNECTION_STRING"))
db = client.get_database("qr_codes")
collection = db.get_collection("qr_codes")


def hash_string(string_in: str):
    result = hashlib.md5(string_in.encode())
    return result.hexdigest()


class BaseModel(PydanticBaseModel):
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.timestamp(),
        }

    def to_document_dict(self):
        return json.loads(self.json())


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
    background: str
    primary: Optional[str]
    secondary: Optional[str]


class CreateQRCodeAPIRequest(BaseModel):
    name: str
    target_url: str
    drawer: Optional[QRCodeDrawers]
    mask: Optional[QRCodeMasks]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    background_color: Optional[str]


class GetQRCodeAPIResponse(BaseModel):
    name: str
    qr_link: str
    target_url: str
    scan_counter: int = 0
    identifier: str
    image: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @root_validator(pre=True)
    def set_name(cls, values):
        if "name" not in values:
            values["name"] = extract_domain_from_url(values["target_url"])
        return values


class GetPreviewAPIResponse(BaseModel):
    image: str


class GetPreviewAPIRequest(BaseModel):
    drawer: Optional[QRCodeDrawers]
    mask: Optional[QRCodeMasks]


class QRCodeEntryDB(BaseModel):
    qr_link: str
    target_url: str
    scan_counter: int = 0
    identifier: str
    image: str
    name: str


class PageResponse(BaseModel):
    kind: str = BaseModel.__name__
    items: list[BaseModel]
    page: int
    page_size: int
    next_page: Optional[int]


class ListQRCodeAPIResponse(PageResponse):
    items: list[GetQRCodeAPIResponse]
    kind: str = GetQRCodeAPIResponse.__name__


class ListQrCodeAPIRequset(BaseModel):
    page: int = 1
    page_size: int = 10


@app.get("/health")
async def health():
    return {"health": "ok"}


def extract_domain_from_url(url):
    return url.split("/")[2]


class RGBColor(tuple):
    def __new__(cls, value):
        try:
            return cls.from_hex_color(cls, value)
        except TypeError:
            pass
        if not isinstance(value, tuple):
            raise TypeError("Expected tuple")
        if len(value) != 3:
            raise ValueError("Expected tuple of length 3")
        return tuple.__new__(cls, value)

    def __repr__(self) -> str:
        return f"<RGBColor({self[0]}, {self[1]}, {self[2]})>"

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def from_hex_color(cls, hex_color: str) -> "RGBColor":
        return HEXColor(hex_color).to_rgb_color()


class HEXColor(str):
    def __new__(cls, value):
        if not isinstance(value, str):
            raise TypeError("Expected string")
        if not value.startswith("#"):
            raise ValueError("Expected string starting with #")
        if len(value) != 7:
            raise ValueError("Expected string of length 7")
        return str.__new__(cls, value)

    def __repr__(self) -> str:
        return f"<HEXColor({self})>"

    def __str__(self) -> str:
        return self.__repr__()

    def to_rgb_color(self) -> RGBColor:
        return RGBColor((int(self[1:3], 16), int(self[3:5], 16), int(self[5:7], 16)))


def hex_to_rgb(*args) -> Optional[RGBColor]:
    hex_color = args[0]
    if not hex_color:
        return None
    return HEXColor(hex_color).to_rgb_color()


def map_drawers(drawer: QRCodeDrawers) -> moduledrawers.QRModuleDrawer:
    return {
        QRCodeDrawers.CIRCLE_MODULE: moduledrawers.CircleModuleDrawer(),
        QRCodeDrawers.GAPPED_SQUARE_MODULE: moduledrawers.GappedSquareModuleDrawer(),
        QRCodeDrawers.HORIZONTAL_BARS: moduledrawers.HorizontalBarsDrawer(),
        QRCodeDrawers.ROUNDED_MODULE: moduledrawers.RoundedModuleDrawer(),
        QRCodeDrawers.SQUARE_MODULE: moduledrawers.SquareModuleDrawer(),
        QRCodeDrawers.VERTICAL_BARS: moduledrawers.VerticalBarsDrawer(),
    }.get(drawer, moduledrawers.SquareModuleDrawer())


def mask_factory(
    mask: Optional[QRCodeMasks] = None,
    background_color: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
) -> colormasks.QRColorMask:
    return {
        QRCodeMasks.HORIZONTAL_GRADIENT: partial(
            colormasks.HorizontalGradiantColorMask,
            back_color=background_color,
            left_color=primary_color,
            right_color=secondary_color,
        ),
        QRCodeMasks.IMAGE_COLOR: partial(
            colormasks.ImageColorMask, back_color=background_color
        ),
        QRCodeMasks.RADIAL_GRADIENT: partial(
            colormasks.RadialGradiantColorMask,
            back_color=background_color,
            center_color=primary_color,
            edge_color=secondary_color,
        ),
        QRCodeMasks.SOLID_FILL: partial(
            colormasks.SolidFillColorMask,
            back_color=background_color,
            front_color=primary_color,
        ),
        QRCodeMasks.SQUARE_GRADIENT: partial(
            colormasks.SquareGradiantColorMask,
            back_color=background_color,
            center_color=primary_color,
            edge_color=secondary_color,
        ),
        QRCodeMasks.VERTICAL_GRADIENT: partial(
            colormasks.VerticalGradiantColorMask,
            back_color=background_color,
            top_color=primary_color,
            bottom_color=secondary_color,
        ),
    }.get(
        mask,
        partial(
            colormasks.SolidFillColorMask,
            back_color=background_color,
            front_color=primary_color,
        ),
    )()


def make_qr_code(
    data: str,
    drawer: Optional[QRCodeDrawers] = None,
    mask: Optional[QRCodeMasks] = None,
    background_color: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
):
    primary_color = (
        RGBColor.from_hex_color(primary_color) if primary_color else RGBColor((0, 0, 0))
    )
    secondary_color = (
        RGBColor.from_hex_color(secondary_color)
        if secondary_color
        else RGBColor((125, 125, 125))
    )
    background_color = (
        RGBColor.from_hex_color(background_color)
        if background_color
        else RGBColor((255, 255, 255))
    )
    mask_instance = mask_factory(mask, background_color, primary_color, secondary_color)
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        image_factory=StyledPilImage,
    )
    qr.add_data(f"{data}")
    img = qr.make_image(
        module_drawer=map_drawers(drawer),
        color_mask=mask_instance,
    )
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return img_buffer


@app.get("/qr", response_model=ListQRCodeAPIResponse)
async def fetch_qr_codes(request: Request, page: int = 1, page_size: int = 10):
    logger.info("Fetching QR codes")
    results = list(collection.find().skip((page - 1) * page_size).limit(page_size))
    logger.info("Found %s QR codes", len(results))
    return ListQRCodeAPIResponse(
        items=[GetQRCodeAPIResponse(**result) for result in results],
        page=page,
        page_size=page_size,
        next_page=page + 1 if len(results) == page_size else None,
    )


@app.get("/qr-preview", response_model=GetPreviewAPIResponse)
def get_qr_code_preview(
    request: Request,
    drawer: Optional[QRCodeDrawers] = None,
    mask: Optional[QRCodeMasks] = None,
    background_color: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
):
    logger.info("Creating QR code preview")
    img_buffer = make_qr_code(
        request.base_url, drawer, mask, background_color, primary_color, secondary_color
    )
    return GetPreviewAPIResponse(
        image=base64.b64encode(img_buffer.getvalue()).decode("utf-8"),
    )


@app.post("/qr", response_model=GetQRCodeAPIResponse)
async def create_qr_code(payload: CreateQRCodeAPIRequest, request: Request):
    logger.info("Creating QR code")
    name = payload.name or extract_domain_from_url(payload.target_url)
    img_name = hash_string(payload.target_url)
    img_buffer = make_qr_code(
        f"{request.base_url}scan/{img_name}",
        payload.drawer,
        payload.mask,
        payload.background_color,
        payload.primary_color,
        payload.secondary_color,
    )
    qr_db_instance = QRCodeEntryDB(
        name=name,
        target_url=payload.target_url,
        qr_link=f"{request.url._url}/{img_name}/png",
        identifier=img_name,
        image=base64.b64encode(img_buffer.read()),
    )
    collection.insert_one(qr_db_instance.to_document_dict())
    return GetQRCodeAPIResponse(**qr_db_instance.dict())


@app.get("/qr/{identifier}")
async def get_qr_data(identifier: str, request: Request):
    logger.info("Fetching QR code %s", identifier)
    document = collection.find_one({"identifier": identifier})
    if not document:
        return Response(status_code=HTTPStatus.NOT_FOUND)
    return GetQRCodeAPIResponse(**document)


@app.get("/qr/{identifier}/png")
async def get_qr_data(identifier: str, request: Request):
    logger.info("Fetching QR code PNG %s", identifier)
    document = collection.find_one({"identifier": identifier})
    if not document:
        return Response(status_code=HTTPStatus.NOT_FOUND)
    return StreamingResponse(
        io.BytesIO(base64.b64decode(document["image"])), media_type="image/png"
    )


@app.get("/scan/{identifier}")
async def redirect_scan(identifier: str, request: Request):
    logger.info("QR code %s was scanned", identifier)
    document = collection.find_one({"identifier": identifier})
    if not document:
        return Response(status_code=HTTPStatus.NOT_FOUND)
    collection.update_one(
        {"identifier": identifier},
        {"$set": {"scan_counter": document["scan_counter"] + 1}},
    )
    return RedirectResponse(document["target_url"])
