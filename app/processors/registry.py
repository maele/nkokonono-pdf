from app.processors.base import BaseProcessor
from app.processors.compare import CompareProcessor
from app.processors.compress import CompressProcessor
from app.processors.delete import DeleteProcessor
from app.processors.extract import ExtractProcessor
from app.processors.headers_footers import HeadersFootersProcessor
from app.processors.html_to_pdf import HtmlToPdfProcessor
from app.processors.images_to_pdf import ImagesToPdfProcessor
from app.processors.merge import MergeProcessor
from app.processors.metadata import MetadataProcessor
from app.processors.ocr import OcrProcessor
from app.processors.office_to_pdf import ExcelToPdfProcessor, PptToPdfProcessor, WordToPdfProcessor
from app.processors.organise import OrganiseProcessor
from app.processors.page_numbers import PageNumbersProcessor
from app.processors.pdf_to_images import PdfToImagesProcessor
from app.processors.pdf_to_office import PdfToExcelProcessor, PdfToPptProcessor, PdfToWordProcessor
from app.processors.repair import RepairProcessor
from app.processors.rotate import RotateProcessor
from app.processors.security import ProtectProcessor, UnlockProcessor
from app.processors.split import SplitProcessor
from app.processors.watermark import WatermarkProcessor

_CLASSES: tuple[type[BaseProcessor], ...] = (
    MergeProcessor, SplitProcessor, CompressProcessor, OrganiseProcessor,
    ExtractProcessor, RotateProcessor, DeleteProcessor, ImagesToPdfProcessor,
    PdfToImagesProcessor, ProtectProcessor, UnlockProcessor, MetadataProcessor,
    WatermarkProcessor, PageNumbersProcessor, HeadersFootersProcessor,
    RepairProcessor, CompareProcessor,
    WordToPdfProcessor, ExcelToPdfProcessor, PptToPdfProcessor,
    PdfToWordProcessor, PdfToExcelProcessor, PdfToPptProcessor,
    HtmlToPdfProcessor, OcrProcessor,
)

PROCESSORS: dict[str, BaseProcessor] = {cls.tool_name: cls() for cls in _CLASSES}


def get_processor(tool_name: str) -> BaseProcessor | None:
    return PROCESSORS.get(tool_name)