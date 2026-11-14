from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError


MAX_ADMISSION_DOCUMENT_BYTES = 10 * 1024 * 1024
SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def validate_admission_document(uploaded_file):
    if uploaded_file.size > MAX_ADMISSION_DOCUMENT_BYTES:
        raise ValidationError("Admission documents must be 10 MB or smaller.")
    extension = Path(uploaded_file.name).suffix.lower()
    signatures = SIGNATURES.get(extension)
    if not signatures:
        raise ValidationError("Upload a PDF, JPEG, or PNG document.")
    position = uploaded_file.tell()
    signature = uploaded_file.read(8)
    uploaded_file.seek(position)
    if not any(signature.startswith(expected) for expected in signatures):
        raise ValidationError("The uploaded file content does not match its file type.")


def admission_document_upload_to(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"admissions/requirements/{uuid4().hex}{extension}"
