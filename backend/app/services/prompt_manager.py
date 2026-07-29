import os
import logging

logger = logging.getLogger("document_ocr.prompt_manager")

class PromptManager:
    """
    Service responsible for loading, caching, and formatting prompt template files.
    """
    def __init__(self) -> None:
        self.prompts_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../prompts")
        )
        self._prompt_cache = {}

    def load_prompts(self) -> None:
        """
        Loads all prompt .txt files from app/prompts/ and caches them in memory.
        """
        logger.info(f"Loading prompt templates from directory: {self.prompts_dir}")
        if not os.path.exists(self.prompts_dir):
            logger.warning(f"Prompts directory '{self.prompts_dir}' does not exist.")
            return

        try:
            for file_name in os.listdir(self.prompts_dir):
                if file_name.endswith(".txt"):
                    name, _ = os.path.splitext(file_name)
                    path = os.path.join(self.prompts_dir, file_name)
                    with open(path, "r", encoding="utf-8") as f:
                        self._prompt_cache[name] = f.read()
            logger.info(f"Successfully loaded and cached {len(self._prompt_cache)} prompt templates.")
        except Exception as e:
            logger.error(f"Error loading prompt templates: {str(e)}")

    def get_prompt(self, name: str, **kwargs) -> str:
        """
        Retrieves a cached prompt template by name and formats it with keyword variables.
        """
        template = self._prompt_cache.get(name)
        if not template:
            # Fallback to load dynamically or raise error
            path = os.path.join(self.prompts_dir, f"{name}.txt")
            if os.path.exists(path):
                logger.info(f"Loading prompt template '{name}' dynamically from disk.")
                with open(path, "r", encoding="utf-8") as f:
                    template = f.read()
                self._prompt_cache[name] = template
            else:
                raise FileNotFoundError(f"Prompt template '{name}' could not be resolved.")
                
        # Perform explicit string substitution to avoid format() KeyError on JSON curly braces
        result = template
        for k, v in kwargs.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result

# Instantiate PromptManager singleton
prompt_manager = PromptManager()
