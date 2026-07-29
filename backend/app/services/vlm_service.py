import time
import logging
import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from app.core.config import settings
from app.exceptions.handlers import VLMInferenceException, VLMModelLoadingException

logger = logging.getLogger("document_ocr.vlm_service")

class VLMService:
    """
    Service to manage the lifecycle and inference of the Qwen2.5-VL Vision Language Model.
    Designed as a singleton to load the model once into memory and reuse it.
    """
    def __init__(self) -> None:
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float32
        
        # Select best available dtype for GPU or CPU
        if self.device == "cuda":
            if torch.cuda.is_bf16_supported():
                self.torch_dtype = torch.bfloat16
                logger.info("CUDA is available and supports bfloat16. Using torch.bfloat16.")
            else:
                self.torch_dtype = torch.float16
                logger.info("CUDA is available. Using torch.float16.")
        else:
            self.torch_dtype = torch.float32
            logger.info("CUDA is unavailable. Running on CPU. Using torch.float32.")

    def load_model(self) -> None:
        """
        Loads the Qwen2.5-VL model and processor once during startup.
        """
        if settings.MOCK_VLM:
            logger.info("MOCK_VLM is enabled. Skipping Hugging Face model download and load.")
            return

        logger.info(f"Initiating VLM model load: {settings.MODEL_ID} on device: {self.device}")
        start_time = time.time()
        
        try:
            # 1. Load the AutoProcessor
            self.processor = AutoProcessor.from_pretrained(settings.MODEL_ID)
            logger.info("Successfully loaded AutoProcessor.")
            
            # 2. Load the Model with matching precision configurations
            if self.device == "cuda":
                # Auto-allocation on GPUs using device_map="auto"
                self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    settings.MODEL_ID,
                    torch_dtype=self.torch_dtype,
                    device_map="auto"
                )
            else:
                # Direct allocation to CPU
                self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    settings.MODEL_ID,
                    torch_dtype=self.torch_dtype,
                    device_map="cpu"
                )
                
            elapsed = time.time() - start_time
            logger.info(f"VLM Model and Processor loaded successfully in {elapsed:.2f} seconds.")
            
        except Exception as e:
            logger.error(f"Failed to load VLM model: {str(e)}")
            raise VLMModelLoadingException(f"Startup model load failed for '{settings.MODEL_ID}': {str(e)}")

    async def perform_ocr(self, image: Image.Image) -> str:
        """
        Runs inference on the provided PIL image using a structured prompt to perform raw text extraction.
        Returns the extracted text as a string.
        """
        if settings.MOCK_VLM:
            import asyncio
            logger.info("MOCK_VLM is enabled. Simulating OCR inference and returning mock text.")
            await asyncio.sleep(1.0)  # Simulate non-blocking model processing delay
            return (
                "Document OCR Mock Output:\n\n"
                "This is a mocked OCR text output from Qwen2.5-VL-3B-Instruct.\n"
                "The VLM model download was bypassed because MOCK_VLM is enabled in the configuration.\n\n"
                "You can start testing your frontend integration and other system behaviors immediately!"
            )

        if self.model is None or self.processor is None:
            logger.error("Attempted VLM OCR request, but model is not loaded in memory.")
            raise VLMInferenceException("VLM model is not loaded. Ensure it loaded properly on startup.")
        
        # 1. Ensure image is in standard RGB format
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        # 2. Define the exact system/OCR prompt requested
        prompt = (
            "You are an OCR assistant.\n"
            "Read the entire document carefully.\n"
            "Extract all visible text exactly as written.\n"
            "Preserve line breaks.\n"
            "Do not summarize.\n"
            "Do not explain.\n"
            "Only output the extracted text."
        )
        
        # 3. Build Hugging Face message list
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        logger.info("Preparing inputs for VLM inference...")
        inference_start = time.time()
        
        try:
            # Apply chat templates formatting
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            # Format visual structures (dynamic FPS/resolution selection)
            image_inputs, video_inputs = process_vision_info(messages)
            
            # Form processor tensors
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )
            
            # Move all input tensors to target device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            logger.info("Executing generation on model...")
            # Run model generation
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=2048  # Large enough token limit for complex text document extraction
                )
                
            # Trim the prompt tokens from the output IDs
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
            ]
            
            # Decode the response into text
            output_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )
            
            elapsed = time.time() - inference_start
            logger.info(f"VLM Inference complete in {elapsed:.2f} seconds.")
            
            if not output_text or len(output_text) == 0:
                raise VLMInferenceException("Model failed to generate a valid text response.")
                
            return output_text[0]
            
        except torch.cuda.OutOfMemoryError as oom:
            logger.error("Out of Memory (OOM) error encountered during GPU inference!")
            if self.device == "cuda":
                torch.cuda.empty_cache()
            raise oom
        except Exception as e:
            logger.error(f"Failed to perform VLM OCR: {str(e)}")
            raise VLMInferenceException(f"VLM execution failed during inference: {str(e)}")

    async def run_inference(self, prompt: str, image: Image.Image = None) -> str:
        """
        Runs a general text or vision-language inference using the loaded Qwen2.5-VL model.
        Returns the decoded output string.
        """
        if settings.MOCK_VLM:
            logger.info("MOCK_VLM is enabled. Skipping model inference.")
            return ""

        if self.model is None or self.processor is None:
            logger.error("VLM inference request failed: model not loaded.")
            raise VLMInferenceException("VLM model is not loaded in memory.")

        # Build message structure
        content = []
        if image is not None:
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            content.append({"type": "image", "image": image})
        
        content.append({"type": "text", "text": prompt})
        
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]

        logger.info("Initiating VLM prompt execution...")
        start_time = time.time()

        try:
            # Apply chat templates
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            # Format visual structures
            image_inputs, video_inputs = process_vision_info(messages)
            
            # Form processor tensors
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )
            
            # Move inputs to target device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=1024  # Limit JSON responses to 1024 tokens
                )
                
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
            ]
            
            output_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )
            
            elapsed = time.time() - start_time
            logger.info(f"VLM prompt execution finished in {elapsed:.2f} seconds.")
            
            if not output_text or len(output_text) == 0:
                raise VLMInferenceException("VLM generated an empty response.")
                
            return output_text[0]
            
        except torch.cuda.OutOfMemoryError as oom:
            logger.error("Out of Memory (OOM) error encountered during GPU inference!")
            if self.device == "cuda":
                torch.cuda.empty_cache()
            raise oom
        except Exception as e:
            logger.error(f"Failed to run VLM inference: {str(e)}")
            raise VLMInferenceException(f"VLM execution failed during inference: {str(e)}")

# Singleton instance of the VLMService
vlm_service = VLMService()
