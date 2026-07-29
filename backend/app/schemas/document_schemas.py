from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Invoice Schema ---
class InvoiceItem(BaseModel):
    description: str = Field(..., description="Item description.")
    quantity: Optional[Any] = Field(None, description="Item quantity.")
    unit_price: Optional[Any] = Field(None, description="Item unit price.")
    amount: Optional[Any] = Field(None, description="Line amount.")

class InvoiceData(BaseModel):
    vendor_name: Optional[str] = Field(None, description="Name of the vendor/supplier.")
    invoice_number: Optional[str] = Field(None, description="Invoice reference number.")
    invoice_date: Optional[str] = Field(None, description="Invoice issue date.")
    due_date: Optional[str] = Field(None, description="Payment due date.")
    currency: Optional[str] = Field(None, description="Currency indicator.")
    subtotal: Optional[Any] = Field(None, description="Subtotal amount before taxes.")
    tax: Optional[Any] = Field(None, description="Tax amount.")
    total_amount: Optional[Any] = Field(None, description="Total invoice amount.")
    items: List[InvoiceItem] = Field(default_factory=list, description="List of invoiced line items.")

# --- Receipt Schema ---
class ReceiptItem(BaseModel):
    description: str = Field(..., description="Item description.")
    quantity: Optional[Any] = Field(None, description="Item quantity.")
    amount: Optional[Any] = Field(None, description="Line amount.")

class ReceiptData(BaseModel):
    merchant: Optional[str] = Field(None, description="Name of the store/merchant.")
    date: Optional[str] = Field(None, description="Transaction date.")
    time: Optional[str] = Field(None, description="Transaction time.")
    payment_method: Optional[str] = Field(None, description="Payment method used.")
    total: Optional[Any] = Field(None, description="Total amount.")
    tax: Optional[Any] = Field(None, description="Tax amount.")
    items: List[ReceiptItem] = Field(default_factory=list, description="List of receipt line items.")

# --- Resume Schema ---
class EducationEntry(BaseModel):
    institution: str = Field(..., description="Name of school/university.")
    degree: Optional[str] = Field(None, description="Degree earned.")
    field_of_study: Optional[str] = Field(None, description="Major/Field of study.")
    start_date: Optional[str] = Field(None, description="Start date.")
    end_date: Optional[str] = Field(None, description="End/Graduation date.")

class ExperienceEntry(BaseModel):
    company: str = Field(..., description="Name of the employer.")
    position: Optional[str] = Field(None, description="Job title.")
    start_date: Optional[str] = Field(None, description="Start date.")
    end_date: Optional[str] = Field(None, description="End date.")
    description: Optional[str] = Field(None, description="Roles/responsibilities.")

class ResumeData(BaseModel):
    name: Optional[str] = Field(None, description="Full name.")
    email: Optional[str] = Field(None, description="Email address.")
    phone: Optional[str] = Field(None, description="Phone number.")
    education: List[EducationEntry] = Field(default_factory=list, description="Education details.")
    skills: List[str] = Field(default_factory=list, description="List of technical/soft skills.")
    projects: List[str] = Field(default_factory=list, description="List of project highlights.")
    experience: List[ExperienceEntry] = Field(default_factory=list, description="Work experience.")

# --- Passport Schema ---
class PassportData(BaseModel):
    country: Optional[str] = Field(None, description="Passport issuing country.")
    passport_number: Optional[str] = Field(None, description="Passport identifier.")
    surname: Optional[str] = Field(None, description="Family surname.")
    given_name: Optional[str] = Field(None, description="Given names.")
    nationality: Optional[str] = Field(None, description="Nationality.")
    date_of_birth: Optional[str] = Field(None, description="Date of birth.")
    expiry_date: Optional[str] = Field(None, description="Passport expiration date.")

# --- Aadhaar Schema ---
class AadhaarData(BaseModel):
    name: Optional[str] = Field(None, description="Full name.")
    aadhaar_number: Optional[str] = Field(None, description="Aadhaar UID number.")
    dob: Optional[str] = Field(None, description="Date of birth.")
    gender: Optional[str] = Field(None, description="Gender.")

# --- PAN Schema ---
class PANData(BaseModel):
    name: Optional[str] = Field(None, description="Full name.")
    father_name: Optional[str] = Field(None, description="Father's name.")
    pan_number: Optional[str] = Field(None, description="PAN number.")
    dob: Optional[str] = Field(None, description="Date of birth.")

# --- Driving License Schema ---
class DrivingLicenseData(BaseModel):
    name: Optional[str] = Field(None, description="Full name.")
    license_number: Optional[str] = Field(None, description="License reference number.")
    dob: Optional[str] = Field(None, description="Date of birth.")
    issue_date: Optional[str] = Field(None, description="License issue date.")
    expiry_date: Optional[str] = Field(None, description="License expiration date.")
    address: Optional[str] = Field(None, description="Address.")

# --- Bank Statement Schema ---
class BankStatementData(BaseModel):
    bank_name: Optional[str] = Field(None, description="Name of the bank.")
    account_holder: Optional[str] = Field(None, description="Name of the account holder.")
    account_number: Optional[str] = Field(None, description="Account number.")
    statement_period: Optional[str] = Field(None, description="Statement period range.")
    starting_balance: Optional[Any] = Field(None, description="Balance at start of statement.")
    ending_balance: Optional[Any] = Field(None, description="Balance at end of statement.")

# --- Utility Bill Schema ---
class UtilityBillData(BaseModel):
    biller_name: Optional[str] = Field(None, description="Name of the utility provider.")
    customer_name: Optional[str] = Field(None, description="Name of the customer.")
    account_number: Optional[str] = Field(None, description="Customer account number.")
    bill_date: Optional[str] = Field(None, description="Utility bill issue date.")
    due_date: Optional[str] = Field(None, description="Payment due date.")
    amount_due: Optional[Any] = Field(None, description="Total amount due.")

# --- Generic Document Schema ---
class GenericDocumentData(BaseModel):
    title: Optional[str] = Field(None, description="Title of the document.")
    summary: Optional[str] = Field(None, description="Extracted summary of contents.")
    key_details: Dict[str, Any] = Field(default_factory=dict, description="Custom key-value pairs.")
