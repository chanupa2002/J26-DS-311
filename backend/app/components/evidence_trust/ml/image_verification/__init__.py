"""Foundation for asynchronous evidence-photo verification."""

from .contracts import CheckResult, ImageInput, ImageReport
from .pipeline import ImageVerificationPipeline

__all__ = ["CheckResult", "ImageInput", "ImageReport", "ImageVerificationPipeline"]
