"""Google Cloud service wrappers. All optional — gracefully no-op when unconfigured.

Configured via env:
  GCP_PROJECT_ID       — required for any GCP service
  DOCAI_PROCESSOR_ID   — Document AI OCR processor full resource name
  DOCAI_LOCATION       — e.g. "us" or "asia-south1"
  ENABLE_CLOUD_LOGGING — "1" to ship logs to Cloud Logging
  ENABLE_TTS           — "1" to enable text-to-speech endpoint
  ENABLE_TRANSLATION   — "1" to auto-translate non-English contracts
"""
from __future__ import annotations
import logging
import os
from functools import lru_cache

log = logging.getLogger("lexguard.gcp")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
DOCAI_LOCATION = os.getenv("DOCAI_LOCATION", "us")
DOCAI_PROCESSOR_ID = os.getenv("DOCAI_PROCESSOR_ID", "")
ENABLE_CLOUD_LOGGING = os.getenv("ENABLE_CLOUD_LOGGING", "0") == "1"
ENABLE_TTS = os.getenv("ENABLE_TTS", "0") == "1"
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "0") == "1"


# ---- Cloud Logging --------------------------------------------------------

def setup_cloud_logging() -> None:
    """Attach Google Cloud Logging handler to root logger. No-op if unconfigured."""
    if not ENABLE_CLOUD_LOGGING or not GCP_PROJECT_ID:
        return
    try:
        from google.cloud import logging as gcp_logging
        client = gcp_logging.Client(project=GCP_PROJECT_ID)
        client.setup_logging(log_level=logging.INFO)
        log.info("cloud logging enabled for project %s", GCP_PROJECT_ID)
    except Exception as exc:
        log.warning("cloud logging setup failed: %s", exc)


# ---- Document AI OCR ------------------------------------------------------

@lru_cache(maxsize=1)
def _docai_client():
    from google.cloud import documentai
    from google.api_core.client_options import ClientOptions
    opts = ClientOptions(api_endpoint=f"{DOCAI_LOCATION}-documentai.googleapis.com")
    return documentai.DocumentProcessorServiceClient(client_options=opts)


def docai_extract(file_bytes: bytes, mime_type: str = "application/pdf") -> str | None:
    """Run scanned PDF / image through Document AI OCR. Returns extracted text."""
    if not GCP_PROJECT_ID or not DOCAI_PROCESSOR_ID:
        return None
    try:
        from google.cloud import documentai
        client = _docai_client()
        name = (
            DOCAI_PROCESSOR_ID
            if DOCAI_PROCESSOR_ID.startswith("projects/")
            else f"projects/{GCP_PROJECT_ID}/locations/{DOCAI_LOCATION}/processors/{DOCAI_PROCESSOR_ID}"
        )
        raw = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
        result = client.process_document(request=documentai.ProcessRequest(name=name, raw_document=raw))
        return result.document.text or None
    except Exception as exc:
        log.warning("docai extraction failed: %s", exc)
        return None


# ---- Translation ----------------------------------------------------------

@lru_cache(maxsize=1)
def _translate_client():
    from google.cloud import translate_v2 as translate
    return translate.Client()


def translate_to_english(text: str) -> tuple[str, str]:
    """Translate `text` to English. Returns (translated_text, detected_source_lang)."""
    if not ENABLE_TRANSLATION or not GCP_PROJECT_ID:
        return text, "en"
    try:
        client = _translate_client()
        # truncate to API soft limit ~30k chars per call; for longer docs caller chunks
        result = client.translate(text[:30_000], target_language="en")
        return result["translatedText"], result.get("detectedSourceLanguage", "und")
    except Exception as exc:
        log.warning("translation failed: %s", exc)
        return text, "und"


def detect_language(text: str) -> str:
    """Detect language of text via Translate API; returns 'en' on failure."""
    if not ENABLE_TRANSLATION or not GCP_PROJECT_ID:
        return "en"
    try:
        client = _translate_client()
        result = client.detect_language(text[:2_000])
        return result.get("language", "en")
    except Exception:
        return "en"


# ---- Text-to-Speech -------------------------------------------------------

@lru_cache(maxsize=1)
def _tts_client():
    from google.cloud import texttospeech
    return texttospeech.TextToSpeechClient()


def tts_synthesize(text: str, voice_name: str = "en-US-Neural2-F") -> bytes | None:
    """Convert clause text to MP3 audio bytes. Returns None when TTS disabled."""
    if not ENABLE_TTS:
        return None
    try:
        from google.cloud import texttospeech
        client = _tts_client()
        synthesis_input = texttospeech.SynthesisInput(text=text[:5_000])
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_name[:5],
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95,
        )
        resp = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return resp.audio_content
    except Exception as exc:
        log.warning("tts synthesis failed: %s", exc)
        return None
