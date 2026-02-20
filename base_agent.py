"""
BaseAgent — shared foundation for all agents in the hierarchy.

Provides:
  - Claude API access via anthropic.Anthropic()
  - _call_claude()    : single API call with optional tools
  - _extract_text()   : pull TextBlock content from a response
  - _agentic_loop()   : tool_use cycle until end_turn
"""

from typing import Callable, Optional
import anthropic


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "claude-opus-4-6",
        max_tokens: int = 8096,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic()

    # ------------------------------------------------------------------
    # Core API helpers
    # ------------------------------------------------------------------

    def _call_claude(
        self,
        messages: list,
        tools: Optional[list] = None,
    ) -> anthropic.types.Message:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)

    def _extract_text(self, response: anthropic.types.Message) -> str:
        """Concatenate all TextBlock content from a response."""
        texts = [block.text for block in response.content if hasattr(block, "text")]
        return "\n".join(texts) if texts else "[No text response]"

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _agentic_loop(
        self,
        messages: list,
        tools: Optional[list],
        dispatch_fn: Callable[[str, dict], str],
    ) -> str:
        """
        Run the tool_use → result → tool_use cycle until end_turn.

        dispatch_fn(tool_name, tool_input) must return a string result
        for each tool call.
        """
        while True:
            response = self._call_claude(messages, tools)

            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = dispatch_fn(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason — return whatever text is available
                return self._extract_text(response)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    def run(self, task: str, context: Optional[str] = None, depth: int = 0) -> str:
        raise NotImplementedError
