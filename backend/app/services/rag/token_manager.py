from __future__ import annotations

import tiktoken
from app.core.logging import get_logger

logger = get_logger(__name__)

class TokenManager:
    """Manages token counting, truncation, and LLM cost estimation.
    
    Replaces naive word-splitting token estimation with accurate
    tokenizer encodings (BPE).
    """
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding_name = encoding_name
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            logger.warning(f"Unknown encoding {encoding_name}, falling back to cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def truncate_to_max_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to a maximum number of tokens."""
        if not text or max_tokens <= 0:
            return ""
        
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
            
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)
        
    def get_remaining_context(self, max_context_window: int, current_tokens: int) -> int:
        """Calculate remaining tokens in the context window."""
        return max(0, max_context_window - current_tokens)
        
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, provider: str = "openai", model: str = "gpt-4o-mini") -> float:
        """Estimate API cost based on token counts."""
        if provider.lower() == "openai":
            if model == "gpt-4o-mini":
                # $0.15 per 1M input, $0.60 per 1M output
                return (prompt_tokens / 1_000_000) * 0.15 + (completion_tokens / 1_000_000) * 0.60
            elif model == "gpt-4o":
                # $5.00 per 1M input, $15.00 per 1M output
                return (prompt_tokens / 1_000_000) * 5.00 + (completion_tokens / 1_000_000) * 15.00
                
        return 0.0

token_manager = TokenManager()
