import os
import asyncio
import logging
from dotenv import load_dotenv
# Explicitly load the .env file located in the backend folder so local dev settings are read
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
dotenv_path = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
# Default model requested by user
HF_MODEL = os.getenv("HF_MODEL", "google/gemma-3-4b-it")
PROVIDER = os.getenv("PROVIDER", "gemini").lower()


class LLMClient:
    def __init__(self):
        self.provider = PROVIDER

    async def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        # Gemini (Google) integration using the official google-genai SDK.
        # Use the modern SDK instead of manually constructing REST URLs.
        if self.provider == "gemini" and GOOGLE_API_KEY:
            try:
                from google import genai

                model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

                def _call_genai():
                    client = genai.Client(api_key=GOOGLE_API_KEY)
                    # The SDK supports passing a simple string for contents
                    resp = client.models.generate_content(model=model, contents=prompt)
                    # Prefer `text` attribute if present, otherwise fall back to string()
                    return getattr(resp, "text", str(resp))

                resp_text = await asyncio.to_thread(_call_genai)
                if isinstance(resp_text, str) and resp_text:
                    return resp_text
                # if SDK returned no text, fall through to mock
            except Exception as e:
                return await self._mock_response(prompt + f"\n\n[Gemini error: {e}]")

        # TODO: add Azure integration here
        # Hugging Face inference API support
        if self.provider == "huggingface" and HF_API_KEY:
            try:
                import httpx
                model = os.getenv("HF_MODEL", HF_MODEL)
                url = f"https://api-inference.huggingface.co/models/{model}"
                headers = {"Authorization": f"Bearer {HF_API_KEY}", "Accept": "application/json"}
                payload = {"inputs": prompt, "options": {"wait_for_model": True}, "parameters": {"max_new_tokens": int(max_tokens)}}
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(url, headers=headers, json=payload)
                    # If model not found (404) try common MosaicML prefix fallbacks for Gemma
                    if r.status_code == 404:
                        logger.warning("HuggingFace model not found: %s (404). Trying fallback ids.", model)
                        tried = [model]
                        fallbacks = []
                        if not model.startswith("mosaicml/"):
                            fallbacks.append(f"mosaicml/{model}")
                        # explicit common Gemma id
                        fallbacks.append("google/gemma-3-4b-it")
                        data = None
                        for alt in fallbacks:
                            try:
                                logger.debug("Trying HF model fallback: %s", alt)
                                r2 = await client.post(f"https://api-inference.huggingface.co/models/{alt}", headers=headers, json=payload)
                                if r2.status_code == 200:
                                    data = r2.json()
                                    model = alt
                                    logger.info("HuggingFace fallback succeeded with model %s", alt)
                                    break
                                tried.append(alt)
                            except Exception as e:
                                logger.debug("Fallback request failed for %s: %s", alt, e)
                        if data is None:
                            # surface last 404 body in mock
                            body_text = r.text if hasattr(r, 'text') else ''
                            return await self._mock_response(prompt + f"\n\n[HuggingFace 404. Tried: {tried}. Body: {body_text}]")
                    else:
                        r.raise_for_status()
                        data = r.json()
                # Hugging Face inference can return either a string or a list of dicts
                if isinstance(data, list) and len(data) > 0:
                    # e.g. [{'generated_text': '...'}]
                    first = data[0]
                    if isinstance(first, dict):
                        # common key is 'generated_text'
                        if 'generated_text' in first:
                            return first['generated_text']
                        # some models return {'generated_text': ...} nested differently
                        for v in first.values():
                            if isinstance(v, str):
                                return v
                if isinstance(data, dict):
                    # some HF endpoints return {'generated_text': '...'} directly
                    if 'generated_text' in data:
                        return data['generated_text']
                    # or 'outputs' -> text
                    if 'outputs' in data and isinstance(data['outputs'], list):
                        parts = []
                        for o in data['outputs']:
                            if isinstance(o, dict) and 'generated_text' in o:
                                parts.append(o['generated_text'])
                        if parts:
                            return "\n".join(parts)
                # if nothing parsed, fall through to mock with note
                return await self._mock_response(prompt + "\n\n[HuggingFace returned unrecognized response format]")
            except Exception as e:
                return await self._mock_response(prompt + f"\n\n[HuggingFace error: {e}]")

        return await self._mock_response(prompt)

    async def _mock_response(self, prompt: str) -> str:
        # Deterministic, safe fallback used when no cloud key configured.
        await asyncio.sleep(0.05)
        header = prompt.strip().splitlines()[0][:80] if prompt else "(no prompt)"
        summary = f"Auto-generated content for: {header}\n\n"
        if "FILES_SUMMARY:" in prompt:
            tail = prompt.split("FILES_SUMMARY:", 1)[1].strip()
            lines = [l for l in tail.splitlines() if l.strip()]
            summary += "Files found:\n"
            for ln in lines[:20]:
                summary += f"- {ln}\n"
        summary += "\n[This is a mock response. Configure GOOGLE_API_KEY or AZURE_API_KEY in .env for real LLM outputs.]"
        return summary


_client = LLMClient()

async def generate_text(prompt: str, max_tokens: int = 512) -> str:
    return await _client.generate_text(prompt, max_tokens=max_tokens)
