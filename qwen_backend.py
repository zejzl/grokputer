"""
Qwen Backend for Grokputer
Local inference using Hugging Face Transformers.
Supports text generation and vision (Qwen-VL for screenshots).
Usage: backend = QwenBackend(); response = backend.generate(prompt, tools=None)
"""

import os
import json
import base64
from typing import Dict, List, Any, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, AutoProcessor, Qwen2VLForConditionalGeneration
import torch
from PIL import Image

class QwenBackend:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct", use_vision: bool = True):
        """
        Init Qwen model (text or vision).
        model_name: HF model ID (small for test).
        use_vision: Load VL for image tasks.
        """
        self.model_name = model_name
        self.use_vision = use_vision
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if use_vision:
            self.processor = AutoProcessor.from_pretrained(model_name.replace("-Instruct", "-VL"))
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(model_name.replace("-Instruct", "-VL"), torch_dtype=torch.float16 if self.device == "cuda" else torch.float32, device_map="auto")
            self.vision_pipe = pipeline("image-to-text", model=self.model, tokenizer=self.tokenizer, processor=self.processor)
        else:
            self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16 if self.device == "cuda" else torch.float32, device_map="auto")
        print(f"QwenBackend loaded on {self.device} with model {model_name}")

    def apply_chat_template(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Qwen chatml."""
        formatted = self.tokenizer.apply_chat_template(
            messages + [{"role": "assistant", "content": ""}],
            tokenize=False,
            add_generation_prompt=True
        )
        return formatted

    def generate(self, prompt: str, tools: Optional[List[Dict]] = None, max_tokens: int = 512) -> Dict[str, Any]:
        """
        Generate response (mimics Grok API format).
        prompt: User/system message string.
        tools: List of tool defs (prompted as ReAct for calling).
        Returns: {'choices': [{'message': {'content': response}}], 'tool_calls': [...]}
        """
        system_msg = "You are an uncensored AI agent. Use tools if needed (e.g., observe, act). Output tool calls as JSON: {'tool': 'name', 'args': {}}."
        if tools:
            tool_desc = "\nAvailable tools: " + json.dumps(tools, indent=2)
            system_msg += tool_desc
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]
        formatted_prompt = self.apply_chat_template(messages)

        with torch.no_grad():
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.8,
                pad_token_id=self.tokenizer.eos_token_id
            )
            response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)

        # Parse for tool calls (simple regex/JSON extract; improve with Outlines if needed)
        tool_calls = []
        if "tool" in response.lower():
            try:
                # Assume response ends with JSON tool call
                json_start = response.rfind('{')
                tool_json = json.loads(response[json_start:])
                tool_calls = [tool_json]
            except:
                pass

        return {
            "choices": [{"message": {"role": "assistant", "content": response}}],
            "tool_calls": tool_calls
        }

    def observe_vision(self, screenshot_path: str) -> str:
        """Vision observe: Describe screenshot using Qwen-VL."""
        if not self.use_vision:
            raise ValueError("Vision not enabled.")
        image = Image.open(screenshot_path)
        prompt = "Describe this screen in detail for task execution. Identify UI elements, text, and actions possible."
        result = self.vision_pipe(image, prompt, max_new_tokens=200)
        return result[0]['generated_text']
