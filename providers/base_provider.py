from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    @abstractmethod
    def query(self, prompt: str, system_prompt: str) -> dict:
        """
        Execute AI query and return dict containing:
        - text: The generated text response
        - tokens_in: Input tokens used
        - tokens_out: Output tokens used
        - cost_inr: Estimated cost in INR
        """
        pass
