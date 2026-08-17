import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.vlm_service import vlm_service, _HAS_GEMINI
from app.services.prompt_manager import prompt_manager
from app.exceptions.handlers import VLMInferenceException

# Import all schemas
from app.schemas.document_schemas import (
    InvoiceData,
    ReceiptData,
    ResumeData,
    PassportData,
    AadhaarData,
    PANData,
    DrivingLicenseData,
    BankStatementData,
    UtilityBillData,
    GenericDocumentData
)

logger = logging.getLogger("document_ocr.document_service")

# =====================================================================
# Strategy Pattern: Base and Concrete Strategies
# =====================================================================

class BaseExtractionStrategy(ABC):
    """
    Abstract base class for structured document extraction strategies.
    """
    @property
    @abstractmethod
    def document_type(self) -> str:
        """The exact document type name."""
        pass

    @property
    @abstractmethod
    def schema_class(self) -> Type[BaseModel]:
        """The Pydantic schema class to validate the extracted data against."""
        pass

    @property
    @abstractmethod
    def prompt_name(self) -> str:
        """The filename of the prompt template inside app/prompts/ (without .txt extension)."""
        pass


class InvoiceExtractionStrategy(BaseExtractionStrategy):
    document_type = "Invoice"
    schema_class = InvoiceData
    prompt_name = "invoice"


class ReceiptExtractionStrategy(BaseExtractionStrategy):
    document_type = "Receipt"
    schema_class = ReceiptData
    prompt_name = "receipt"


class ResumeExtractionStrategy(BaseExtractionStrategy):
    document_type = "Resume"
    schema_class = ResumeData
    prompt_name = "resume"


class PassportExtractionStrategy(BaseExtractionStrategy):
    document_type = "Passport"
    schema_class = PassportData
    prompt_name = "passport"


class AadhaarExtractionStrategy(BaseExtractionStrategy):
    document_type = "Aadhaar Card"
    schema_class = AadhaarData
    prompt_name = "aadhaar"


class PANExtractionStrategy(BaseExtractionStrategy):
    document_type = "PAN Card"
    schema_class = PANData
    prompt_name = "pan"


class DrivingLicenseExtractionStrategy(BaseExtractionStrategy):
    document_type = "Driving License"
    schema_class = DrivingLicenseData
    prompt_name = "driving_license"


class BankStatementExtractionStrategy(BaseExtractionStrategy):
    document_type = "Bank Statement"
    schema_class = BankStatementData
    prompt_name = "bank_statement"


class UtilityBillExtractionStrategy(BaseExtractionStrategy):
    document_type = "Utility Bill"
    schema_class = UtilityBillData
    prompt_name = "utility_bill"


class GenericDocumentExtractionStrategy(BaseExtractionStrategy):
    document_type = "Generic Document"
    schema_class = GenericDocumentData
    prompt_name = "generic_document"


# =====================================================================
# Factory Pattern: Strategy Factory
# =====================================================================

class ExtractionStrategyFactory:
    """
    Factory to resolve the appropriate extraction strategy for a classified document type.
    """
    def __init__(self, strategies: List[BaseExtractionStrategy]) -> None:
        self._strategies = {s.document_type.lower(): s for s in strategies}

    def get_strategy(self, document_type: str) -> BaseExtractionStrategy:
        # Standardize matching to lower case
        type_key = document_type.lower()
        
        # Maps variants like Aadhaar Card vs Aadhaar
        if "aadhaar" in type_key:
            type_key = "aadhaar card"
        elif "pan" in type_key:
            type_key = "pan card"
            
        strategy = self._strategies.get(type_key)
        if not strategy:
            logger.warning(f"Unknown document type '{document_type}'. Falling back to Generic Document strategy.")
            return self._strategies["generic document"]
            
        return strategy

# Initialize Factory with supported strategies
strategy_factory = ExtractionStrategyFactory([
    InvoiceExtractionStrategy(),
    ReceiptExtractionStrategy(),
    ResumeExtractionStrategy(),
    PassportExtractionStrategy(),
    AadhaarExtractionStrategy(),
    PANExtractionStrategy(),
    DrivingLicenseExtractionStrategy(),
    BankStatementExtractionStrategy(),
    UtilityBillExtractionStrategy(),
    GenericDocumentExtractionStrategy()
])

# =====================================================================
# Orchestrator Service: DocumentService
# =====================================================================

class DocumentService:
    """
    Service responsible for orchestrating document classification, 
    strategy resolution, information extraction, and schema validation.
    """
    def __init__(self, factory: ExtractionStrategyFactory) -> None:
        self.factory = factory

    async def analyze_document(self, ocr_text: str, filename: str) -> dict:
        """
        Coordinates document analysis:
          1. Classifies the document type from OCR text.
          2. Retrieves the concrete strategy using the Factory.
          3. Extracts specific schema details using VLM.
          4. Validates structured JSON using Pydantic.
        """
        start_time = time.time()
        
        # 1. Classify Document Type & Confidence
        doc_type, confidence = await self._classify_document(ocr_text, filename)
        logger.info(f"Classified document '{filename}' as '{doc_type}' with confidence {confidence:.2f}")
        
        # 2. Get Strategy from Factory
        strategy = self.factory.get_strategy(doc_type)
        logger.info(f"Resolved extraction strategy: '{strategy.__class__.__name__}' for type: '{strategy.document_type}'")
        
        # 3. Extract structured detail data
        extracted_data_dict = await self._extract_structured_data(ocr_text, strategy, filename)
        
        elapsed = time.time() - start_time
        logger.info(f"Document analysis completed in {elapsed:.2f} seconds.")
        
        return {
            "success": True,
            "document_type": strategy.document_type,
            "confidence": confidence,
            "data": extracted_data_dict,
            "processing_time": f"{elapsed:.2f}s"
        }

    async def _classify_document(self, ocr_text: str, filename: str) -> tuple[str, float]:
        """
        Classifies OCR text into one of the supported types.
        """
        if settings.MOCK_VLM and not _HAS_GEMINI:
            # Local developer mock classification based on filename hints
            fn_lower = filename.lower()
            if "invoice" in fn_lower:
                return "Invoice", 0.98
            elif "receipt" in fn_lower:
                return "Receipt", 0.95
            elif "resume" in fn_lower or "cv" in fn_lower:
                return "Resume", 0.99
            elif "passport" in fn_lower:
                return "Passport", 0.97
            elif "aadhaar" in fn_lower:
                return "Aadhaar Card", 0.96
            elif "pan" in fn_lower:
                return "PAN Card", 0.96
            elif "license" in fn_lower or "driving" in fn_lower:
                return "Driving License", 0.95
            elif "bank" in fn_lower:
                return "Bank Statement", 0.94
            elif "bill" in fn_lower or "utility" in fn_lower:
                return "Utility Bill", 0.93
            elif "unknown" in fn_lower:
                return "Unknown Document", 0.30  # Triggers fallback to Generic Document
            else:
                return "Generic Document", 0.85

        # Format classification system prompt
        prompt = prompt_manager.get_prompt("classification", ocr_text=ocr_text)
        
        try:
            raw_response = await vlm_service.run_inference(prompt)
            # Parse Qwen JSON output
            clean_json = self._clean_json_response(raw_response)
            classification_data = json.loads(clean_json)
            
            doc_type = classification_data.get("document_type", "Generic Document")
            confidence = float(classification_data.get("confidence", 0.50))
            
            # low confidence maps to Unknown Document
            if confidence < 0.50 or doc_type == "Unknown Document":
                return "Generic Document", confidence
                
            return doc_type, confidence
        except Exception as e:
            logger.error(f"Classification prompt inference failed, falling back to Generic. Details: {str(e)}")
            return "Generic Document", 0.50

    async def _extract_structured_data(self, ocr_text: str, strategy: BaseExtractionStrategy, filename: str) -> dict:
        """
        Runs the extraction prompt for the resolved strategy and validates the output using Pydantic.
        """
        if settings.MOCK_VLM and not _HAS_GEMINI:
            # Return high-fidelity placeholder schema data for local development
            return self._generate_mock_schema_data(strategy.document_type, filename)

        # Get formatted extraction prompt
        prompt = prompt_manager.get_prompt(strategy.prompt_name, ocr_text=ocr_text)
        
        try:
            raw_response = await vlm_service.run_inference(prompt)
            clean_json = self._clean_json_response(raw_response)
            
            # Pydantic Schema Validation
            try:
                validated_model = strategy.schema_class.model_validate_json(clean_json)
                return validated_model.model_dump()
            except ValidationError as val_err:
                logger.error(f"Pydantic Validation failed for model {strategy.schema_class.__name__}: {str(val_err)}")
                # Try parsing raw dict fallback or raise exception
                try:
                    raw_dict = json.loads(clean_json)
                    # Create generic structure or raise to client
                    validated_model = strategy.schema_class.model_validate(raw_dict)
                    return validated_model.model_dump()
                except Exception:
                    raise VLMInferenceException(
                        f"AI extraction output failed structural validation against Pydantic schema '{strategy.schema_class.__name__}': {val_err.errors()}"
                    )
        except Exception as e:
            if isinstance(e, VLMInferenceException):
                raise e
            logger.error(f"Failed structured extraction: {str(e)}")
            raise VLMInferenceException(f"VLM structured extraction failed: {str(e)}")

    def _clean_json_response(self, text: str) -> str:
        """
        Cleans LLM response text from markdown JSON syntax wrappers if returned.
        """
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _generate_mock_schema_data(self, doc_type: str, filename: str) -> dict:
        """
        Generates realistic mockup JSON structures conforming to schema templates for developer mock-mode testing.
        """
        if doc_type == "Invoice":
            return {
                "vendor_name": "ACME Industrial Suppliers Inc.",
                "invoice_number": "INV-2026-9941",
                "invoice_date": "2026-07-20",
                "due_date": "2026-08-20",
                "currency": "USD",
                "subtotal": 1250.00,
                "tax": 100.00,
                "total_amount": 1350.00,
                "items": [
                    {"description": "Vision Processing Unit V1", "quantity": 2, "unit_price": 500.00, "amount": 1000.00},
                    {"description": "Edge AI Interface Cable", "quantity": 5, "unit_price": 50.00, "amount": 250.00}
                ]
            }
        elif doc_type == "Receipt":
            return {
                "merchant": "Starbucks Coffee #4921",
                "date": "2026-07-24",
                "time": "09:42:00",
                "payment_method": "Visa Credit",
                "total": 12.45,
                "tax": 0.95,
                "items": [
                    {"description": "Caffe Latte Venti", "quantity": 1, "amount": 5.75},
                    {"description": "Blueberry Muffin XL", "quantity": 1, "amount": 5.75}
                ]
            }
        elif doc_type == "Resume":
            return {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "+1-555-0199",
                "education": [
                    {"institution": "Stanford University", "degree": "M.S.", "field_of_study": "Computer Science", "start_date": "2020", "end_date": "2022"}
                ],
                "skills": ["Python", "FastAPI", "PyTorch", "Vision Language Models", "SOLID Principles"],
                "projects": ["DocumentOCR QA Agent", "VLM Auto-Classifier"],
                "experience": [
                    {"company": "DeepMind Innovations", "position": "Senior AI Architect", "start_date": "2023", "end_date": "Present", "description": "Led document AI modeling strategies."}
                ]
            }
        elif doc_type == "Passport":
            return {
                "country": "United States of America",
                "passport_number": "A12345678",
                "surname": "SMITH",
                "given_name": "JOHN ALBERT",
                "nationality": "USA",
                "date_of_birth": "1990-05-15",
                "expiry_date": "2030-05-15"
            }
        elif doc_type == "Aadhaar Card":
            return {
                "name": "Aarav Sharma",
                "aadhaar_number": "1234 5678 9012",
                "dob": "15/05/1990",
                "gender": "Male"
            }
        elif doc_type == "PAN Card":
            return {
                "name": "AARAV SHARMA",
                "father_name": "RAJESH SHARMA",
                "pan_number": "ABCDE1234F",
                "dob": "15/05/1990"
            }
        elif doc_type == "Driving License":
            return {
                "name": "John Doe",
                "license_number": "DL-12345-67890",
                "dob": "1990-05-15",
                "issue_date": "2015-06-01",
                "expiry_date": "2035-06-01",
                "address": "123 Main Street, Suite 100, Capital City, CC 12345"
            }
        elif doc_type == "Bank Statement":
            return {
                "bank_name": "Chase Bank N.A.",
                "account_holder": "Jane Doe",
                "account_number": "1234567890",
                "statement_period": "2026-06-01 to 2026-06-30",
                "starting_balance": 5240.50,
                "ending_balance": 7430.20
            }
        elif doc_type == "Utility Bill":
            return {
                "biller_name": "Pacific Gas & Electric (PG&E)",
                "customer_name": "Jane Doe",
                "account_number": "987654321-0",
                "bill_date": "2026-07-10",
                "due_date": "2026-07-31",
                "amount_due": 142.50
            }
        else: # Generic Document
            return {
                "title": "Project Phase 4 Integration Blueprint",
                "summary": "This document specifies layout blueprints for structural document extraction pipelines using strategy design patterns.",
                "key_details": {
                    "author": "Antigravity Dev Team",
                    "creation_date": "2026-07-24"
                }
            }

# Instantiate DocumentService singleton
document_service = DocumentService(strategy_factory)
