"""
_common.py — Shared logic for ComfyUI skill scripts.

Single source of truth for:
- HTTP transport (with retry/backoff, streaming, timeout handling)
- Cloud detection and endpoint mapping (local ComfyUI vs Comfy Cloud)
- Workflow node-type catalogs (param patterns, model loaders, output nodes)
- API-format validation
- Path-traversal-safe file writes
- API-key loading from env / CLI

Stdlib-only by design (with optional `requests` upgrade if installed). Python 3.10+.
"""

from __future__ import annotations

import json
import os
import random
import re
import struct
import sys
import time
import uuid
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

# Optional: prefer `requests` if installed (better redirects, streaming, header handling)
try:
    import requests  # type: ignore[import-not-found]
    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - exercised via stdlib fallback
    HAS_REQUESTS = False
    import urllib.error
    import urllib.request


# =============================================================================
# Constants & catalogs
# =============================================================================

# Single local server: the comfy-cli install on :8188. Comfy Desktop was
# retired 2026-10-23 (consolidated to one endpoint); there is no :8189 anymore.
LOCAL_HOST_CANDIDATES = ("http://127.0.0.1:8188",)


def pick_local_host() -> str:
    """Choose the local ComfyUI server URL.

    Order: the COMFYUI_URL env var (explicit pin), then the single local
    candidate :8188 (the comfy-cli install). If it doesn't answer, returns it
    anyway so errors name the expected server.

    Returns:
        Base URL with no trailing slash.
    """
    import urllib.request as _urlreq  # local import: top-level one is conditional

    env = os.environ.get("COMFYUI_URL")
    if env:
        return env.rstrip("/")
    for url in LOCAL_HOST_CANDIDATES:
        try:
            _urlreq.urlopen(url + "/system_stats", timeout=1).close()
        except Exception:
            continue
        return url
    return LOCAL_HOST_CANDIDATES[0]


DEFAULT_LOCAL_HOST = pick_local_host()
DEFAULT_CLOUD_HOST = "https://cloud.comfy.org"
ENV_API_KEY = "COMFY_CLOUD_API_KEY"  # env var NAME (placeholder, not a secret value)

# Connection / retry defaults
DEFAULT_HTTP_TIMEOUT = 60          # seconds — single-attempt request timeout
DEFAULT_RETRIES = 3                # total attempts including the first
RETRY_BASE_DELAY = 1.0             # seconds — exponential backoff base
RETRY_MAX_DELAY = 30.0             # seconds — cap on backoff
RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504, 522, 524}

# Streaming download chunk size (bytes)
DOWNLOAD_CHUNK_SIZE = 1 << 16  # 64 KiB

# Heuristic: workflows with these node types tend to be slow → larger default timeout
SLOW_OUTPUT_NODES = {
    "VHS_VideoCombine", "SaveAnimatedWEBP", "SaveAnimatedPNG",
    "SaveVideo", "SaveAudio", "SaveAnimateDiffVideo",
    "SVD_img2vid_Conditioning",
    "WanVideoSampler", "HunyuanVideoSampler",
    "CogVideoSampler", "LTXVideoSampler",
}

# ---------------------------------------------------------------------------
# Output node catalog (extensible — community packs add their own)
# ---------------------------------------------------------------------------
OUTPUT_NODES: set[str] = {
    # Built-in
    "SaveImage", "PreviewImage",
    "SaveAudio", "SaveVideo", "PreviewAudio", "PreviewVideo",
    "SaveAnimatedWEBP", "SaveAnimatedPNG",
    # Common community packs
    "VHS_VideoCombine",       # Video Helper Suite
    "ImageSave",              # Was Node Suite
    "Image Save",             # Was Node Suite (alt name)
    "easy imageSave",         # easy-use
    "Image Save With Metadata",
    "PreviewImage|pysssss",   # pysssss preview
    "ShowText|pysssss",
    "SaveLatent",
    "SaveGLB",                # 3D
    "Save3D",
}

# ---------------------------------------------------------------------------
# Folder aliases — handle ComfyUI's gradual folder renames
# ---------------------------------------------------------------------------
# When `check_deps.py` queries `/models/<folder>` and gets 404 / empty,
# it tries each alias in turn. Critical for Comfy Cloud which has fully
# migrated to the new naming (unet → diffusion_models, clip → text_encoders).
FOLDER_ALIASES: dict[str, list[str]] = {
    "unet": ["unet", "diffusion_models"],
    "diffusion_models": ["diffusion_models", "unet"],
    "clip": ["clip", "text_encoders"],
    "text_encoders": ["text_encoders", "clip"],
    "controlnet": ["controlnet", "control_net"],
}


def folder_aliases_for(folder: str) -> list[str]:
    """Return the search order of folder names (primary first)."""
    return FOLDER_ALIASES.get(folder, [folder])


# ---------------------------------------------------------------------------
# Model-loader catalog: class_type -> (input field, model folder)
# ---------------------------------------------------------------------------
# A loader can have multiple fields (e.g., DualCLIPLoader has clip_name1 and
# clip_name2). We list them with explicit entries. The folder name is the
# *canonical* one; FOLDER_ALIASES is consulted when querying.
MODEL_LOADERS: dict[str, list[tuple[str, str]]] = {
    # Checkpoints
    "CheckpointLoaderSimple":   [("ckpt_name", "checkpoints")],
    "CheckpointLoader":         [("ckpt_name", "checkpoints")],
    "CheckpointLoader (Simple)": [("ckpt_name", "checkpoints")],
    "ImageOnlyCheckpointLoader": [("ckpt_name", "checkpoints")],
    "unCLIPCheckpointLoader":   [("ckpt_name", "checkpoints")],
    # LoRA
    "LoraLoader":               [("lora_name", "loras")],
    "LoraLoaderModelOnly":      [("lora_name", "loras")],
    "LoraLoaderTagsQuery":      [("lora_name", "loras")],
    # VAE
    "VAELoader":                [("vae_name", "vae")],
    # ControlNet
    "ControlNetLoader":         [("control_net_name", "controlnet")],
    "DiffControlNetLoader":     [("control_net_name", "controlnet")],
    "ControlNetLoaderAdvanced": [("control_net_name", "controlnet")],
    # CLIP / text encoders (primary "clip" folder; check_deps tries text_encoders too)
    "CLIPLoader":               [("clip_name", "clip")],
    "DualCLIPLoader":           [("clip_name1", "clip"), ("clip_name2", "clip")],
    "TripleCLIPLoader":         [("clip_name1", "clip"), ("clip_name2", "clip"), ("clip_name3", "clip")],
    "CLIPVisionLoader":         [("clip_name", "clip_vision")],
    # UNET / Diffusion model (primary "unet"; check_deps tries diffusion_models too)
    "UNETLoader":               [("unet_name", "unet")],
    "DiffusionModelLoader":     [("model_name", "diffusion_models")],
    # GGUF loaders. BOTH the leejet fork and the original city96 node use these
    # class names; registering them is what lets check_deps actually validate
    # .gguf model deps instead of silently reporting is_ready on a workflow
    # whose weights were never downloaded.
    "UNETLoaderGGUF":           [("unet_name", "unet")],
    "UnetLoaderGGUF":           [("unet_name", "unet")],
    "CLIPLoaderGGUF":           [("clip_name", "clip")],
    # Upscaler
    "UpscaleModelLoader":       [("model_name", "upscale_models")],
    # Style / GLIGEN / Hypernetwork
    "StyleModelLoader":         [("style_model_name", "style_models")],
    "GLIGENLoader":             [("gligen_name", "gligen")],
    "HypernetworkLoader":       [("hypernetwork_name", "hypernetworks")],
    # IPAdapter family (community).
    # Note: IPAdapterUnifiedLoader's `preset` and IPAdapterInsightFaceLoader's
    # `provider` are enums (not file paths), so they're intentionally omitted —
    # check_deps would otherwise treat enum values as missing model files.
    "IPAdapterModelLoader":     [("ipadapter_file", "ipadapter")],
    "InstantIDModelLoader":     [("instantid_file", "instantid")],
    # AnimateDiff / video
    "ADE_LoadAnimateDiffModel": [("model_name", "animatediff_models")],
    "ADE_AnimateDiffLoaderWithContext": [("model_name", "animatediff_models")],
    "ADE_AnimateDiffLoaderGen1": [("model_name", "animatediff_models")],
    # Photomaker
    "PhotoMakerLoader":         [("photomaker_model_name", "photomaker")],
    # Sampler / scheduler models
    "ModelSamplingFlux":        [],  # parametric only
}

# ---------------------------------------------------------------------------
# Param patterns: (class_type, field_name) -> friendly_name
# Order matters — first match wins for naming. Use _meta.title for disambiguation.
# ---------------------------------------------------------------------------
PARAM_PATTERNS: list[tuple[str, str, str]] = [
    # ---- Qwen-Image 2.1 (requires ComfyUI >= 0.37.0) ----
    # TextEncodeQwenImage21 takes `prompt` / `negative_prompt` (NOT `text`), and
    # its output 2 is a LATENT — so `prompt` must be a recognized param or
    # run_workflow.py silently drops it from --args.
    ("TextEncodeQwenImage21", "prompt", "prompt"),
    ("TextEncodeQwenImage21", "negative_prompt", "negative_prompt"),
    ("TextEncodeQwenImage21", "resolution", "resolution"),
    ("TextEncodeQwenImageEdit", "prompt", "prompt"),
    ("TextEncodeQwenImageEdit", "negative_prompt", "negative_prompt"),
    ("TextEncodeQwenImageEditPlus", "prompt", "prompt"),
    ("TextEncodeQwenImageEditPlus", "negative_prompt", "negative_prompt"),
    ("EmptyQwenImageLayeredLatentImage", "width", "width"),
    ("EmptyQwenImageLayeredLatentImage", "height", "height"),

    # ---- Prompts ----
    ("CLIPTextEncode", "text", "prompt"),
    ("CLIPTextEncodeSDXL", "text_g", "prompt"),
    ("CLIPTextEncodeSDXL", "text_l", "prompt_l"),
    ("CLIPTextEncodeSDXLRefiner", "text", "refiner_prompt"),
    ("CLIPTextEncodeFlux", "clip_l", "prompt_l"),
    ("CLIPTextEncodeFlux", "t5xxl", "prompt"),
    ("CLIPTextEncodeFlux", "guidance", "guidance"),
    ("smZ CLIPTextEncode", "text", "prompt"),
    ("BNK_CLIPTextEncodeAdvanced", "text", "prompt"),

    # ---- Standard sampling ----
    ("KSampler", "seed", "seed"),
    ("KSampler", "steps", "steps"),
    ("KSampler", "cfg", "cfg"),
    ("KSampler", "sampler_name", "sampler_name"),
    ("KSampler", "scheduler", "scheduler"),
    ("KSampler", "denoise", "denoise"),
    ("KSamplerAdvanced", "noise_seed", "seed"),
    ("KSamplerAdvanced", "steps", "steps"),
    ("KSamplerAdvanced", "cfg", "cfg"),
    ("KSamplerAdvanced", "sampler_name", "sampler_name"),
    ("KSamplerAdvanced", "scheduler", "scheduler"),
    ("KSamplerAdvanced", "start_at_step", "start_at_step"),
    ("KSamplerAdvanced", "end_at_step", "end_at_step"),

    # ---- Modern sampler chain (Flux / SD3 / SDXL refiner via SamplerCustom) ----
    ("RandomNoise", "noise_seed", "seed"),
    ("BasicScheduler", "steps", "steps"),
    ("BasicScheduler", "scheduler", "scheduler"),
    ("BasicScheduler", "denoise", "denoise"),
    ("KSamplerSelect", "sampler_name", "sampler_name"),
    # NB: BasicGuider has no cfg input (it just bundles model+conditioning).
    ("CFGGuider", "cfg", "cfg"),
    ("DualCFGGuider", "cfg_conds", "cfg"),
    ("DualCFGGuider", "cfg_cond2_negative", "cfg_negative"),
    ("ModelSamplingFlux", "max_shift", "max_shift"),
    ("ModelSamplingFlux", "base_shift", "base_shift"),
    ("ModelSamplingFlux", "width", "model_width"),
    ("ModelSamplingFlux", "height", "model_height"),
    ("ModelSamplingSD3", "shift", "shift"),
    ("ModelSamplingDiscrete", "sampling", "sampling"),
    ("SDTurboScheduler", "steps", "steps"),
    ("SDTurboScheduler", "denoise", "denoise"),
    ("SamplerCustom", "noise_seed", "seed"),
    ("SamplerCustom", "cfg", "cfg"),
    # NB: SamplerCustomAdvanced takes a NOISE input (from RandomNoise) — no seed field directly.

    # ---- Dimensions / latent ----
    ("EmptyLatentImage", "width", "width"),
    ("EmptyLatentImage", "height", "height"),
    ("EmptyLatentImage", "batch_size", "batch_size"),
    ("EmptySD3LatentImage", "width", "width"),
    ("EmptySD3LatentImage", "height", "height"),
    ("EmptySD3LatentImage", "batch_size", "batch_size"),
    ("EmptyHunyuanLatentVideo", "width", "width"),
    ("EmptyHunyuanLatentVideo", "height", "height"),
    ("EmptyHunyuanLatentVideo", "length", "length"),
    ("EmptyHunyuanLatentVideo", "batch_size", "batch_size"),
    ("EmptyMochiLatentVideo", "width", "width"),
    ("EmptyMochiLatentVideo", "height", "height"),
    ("EmptyMochiLatentVideo", "length", "length"),
    ("EmptyLTXVLatentVideo", "width", "width"),
    ("EmptyLTXVLatentVideo", "height", "height"),
    ("EmptyLTXVLatentVideo", "length", "length"),
    ("LatentUpscale", "width", "upscale_width"),
    ("LatentUpscale", "height", "upscale_height"),
    ("LatentUpscaleBy", "scale_by", "scale_by"),
    ("ImageScale", "width", "width"),
    ("ImageScale", "height", "height"),

    # ---- Image input ----
    ("LoadImage", "image", "image"),
    ("LoadImageMask", "image", "mask_image"),
    ("LoadImageOutput", "image", "image"),
    ("VHS_LoadVideo", "video", "video"),
    ("VHS_LoadAudio", "audio", "audio"),

    # ---- Model selection (sometimes useful to swap per run) ----
    ("CheckpointLoaderSimple", "ckpt_name", "ckpt_name"),
    ("CheckpointLoader", "ckpt_name", "ckpt_name"),
    ("ImageOnlyCheckpointLoader", "ckpt_name", "ckpt_name"),
    ("VAELoader", "vae_name", "vae_name"),
    ("UNETLoader", "unet_name", "unet_name"),
    ("DiffusionModelLoader", "model_name", "diffusion_model_name"),
    ("UpscaleModelLoader", "model_name", "upscale_model_name"),
    ("CLIPLoader", "clip_name", "clip_name"),
    ("DualCLIPLoader", "clip_name1", "clip_name1"),
    ("DualCLIPLoader", "clip_name2", "clip_name2"),
    ("ControlNetLoader", "control_net_name", "controlnet_name"),

    # ---- LoRA ----
    ("LoraLoader", "lora_name", "lora_name"),
    ("LoraLoader", "strength_model", "lora_strength"),
    ("LoraLoader", "strength_clip", "lora_strength_clip"),
    ("LoraLoaderModelOnly", "lora_name", "lora_name"),
    ("LoraLoaderModelOnly", "strength_model", "lora_strength"),

    # ---- ControlNet ----
    ("ControlNetApply", "strength", "controlnet_strength"),
    ("ControlNetApplyAdvanced", "strength", "controlnet_strength"),
    ("ControlNetApplyAdvanced", "start_percent", "controlnet_start"),
    ("ControlNetApplyAdvanced", "end_percent", "controlnet_end"),

    # ---- IPAdapter ----
    ("IPAdapterAdvanced", "weight", "ipadapter_weight"),
    ("IPAdapterAdvanced", "start_at", "ipadapter_start"),
    ("IPAdapterAdvanced", "end_at", "ipadapter_end"),
    ("IPAdapter", "weight", "ipadapter_weight"),

    # ---- Upscale ----
    ("ImageUpscaleWithModel", "upscale_method", "upscale_method"),

    # ---- AnimateDiff ----
    ("ADE_AnimateDiffLoaderWithContext", "motion_scale", "motion_scale"),
    ("ADE_AnimateDiffLoaderGen1", "motion_scale", "motion_scale"),

    # ---- Video / Save ----
    ("VHS_VideoCombine", "frame_rate", "frame_rate"),
    ("VHS_VideoCombine", "format", "video_format"),
    ("VHS_VideoCombine", "filename_prefix", "filename_prefix"),
    ("SaveImage", "filename_prefix", "filename_prefix"),

    # ---- Hunyuan / Wan / LTX video ----
    ("HunyuanVideoSampler", "seed", "seed"),
    ("HunyuanVideoSampler", "steps", "steps"),
    ("HunyuanVideoSampler", "cfg", "cfg"),
    ("WanVideoSampler", "seed", "seed"),
    ("WanVideoSampler", "steps", "steps"),
    ("WanVideoSampler", "cfg", "cfg"),
    ("LTXVScheduler", "max_shift", "max_shift"),
    ("LTXVScheduler", "base_shift", "base_shift"),

    # ---- rgthree primitives (often used as user-facing inputs) ----
    ("Seed (rgthree)", "seed", "seed"),
    ("Image Comparer (rgthree)", "image_a", "image"),
    ("Power Lora Loader (rgthree)", "PowerLoraLoaderHeaderWidget", "_lora_header"),

    # ---- Easy-use / utility primitives ----
    ("PrimitiveNode", "value", "primitive_value"),
    ("easy seed", "seed", "seed"),
    ("easy positive", "positive", "prompt"),
    ("easy negative", "negative", "negative_prompt"),
    ("easy fullLoader", "ckpt_name", "ckpt_name"),
    ("easy fullLoader", "vae_name", "vae_name"),
    ("easy fullLoader", "lora_name", "lora_name"),
    ("easy fullLoader", "positive", "prompt"),
    ("easy fullLoader", "negative", "negative_prompt"),
]

# Prompt-like fields whose value should be scanned for embedding references
PROMPT_FIELDS = {
    "text", "text_g", "text_l", "t5xxl", "clip_l", "positive", "negative",
    # Qwen-Image 2.1 / edit nodes use bare `prompt` + `negative_prompt`.
    "prompt", "negative_prompt",
}

# Pattern matches: embedding:name, embedding:name.pt, embedding:name:1.2, (embedding:name:1.2)
# Word-boundary at start avoids matching things like "no_embedding:foo".
EMBEDDING_REGEX = re.compile(
    r"(?:^|[\s,(\[])embedding\s*:\s*([A-Za-z0-9_\-\./\\]+?)(?:\.(?:pt|safetensors|bin))?(?=[\s:,)\(\]]|$)",
    re.IGNORECASE,
)


# =============================================================================
# Cloud detection & endpoint routing
# =============================================================================

CLOUD_DOMAIN_SUFFIXES = (".comfy.org",)
CLOUD_DOMAIN_EXACT = {"cloud.comfy.org"}


def is_cloud_host(host: str) -> bool:
    """True if the host points at Comfy Cloud (or staging/preview subdomain)."""
    parsed = urlparse(host if "://" in host else f"http://{host}")
    hostname = (parsed.hostname or "").lower()
    if hostname in CLOUD_DOMAIN_EXACT:
        return True
    return any(hostname.endswith(s) for s in CLOUD_DOMAIN_SUFFIXES)


def build_cloud_aware_url(base: str, path: str, *, force_cloud: bool | None = None) -> str:
    """Build a URL that adds /api prefix when targeting Comfy Cloud.

    Local ComfyUI accepts both `/foo` and `/api/foo` for many endpoints.
    Cloud requires `/api/foo`.

    `path` should be a path component (e.g. "/prompt") or full path with query
    (e.g. "/view?filename=x").
    """
    base = base.rstrip("/")
    cloud = is_cloud_host(base) if force_cloud is None else force_cloud
    if not path.startswith("/"):
        path = "/" + path
    if cloud and not path.startswith("/api/"):
        path = "/api" + path
    return base + path


def cloud_endpoint(path: str) -> str:
    """Map a cloud endpoint path to its current canonical form.

    Handles known renames documented in the Comfy Cloud API:
      /history       -> /history_v2
      /models/<f>    -> /experiment/models/<f>
      /models        -> /experiment/models
    """
    if path.startswith("/history") and not path.startswith("/history_v2"):
        return "/history_v2" + path[len("/history"):]
    if path.startswith("/models/"):
        return "/experiment/models/" + path[len("/models/"):]
    if path == "/models":
        return "/experiment/models"
    return path


def resolve_url(base: str, path: str, *, is_cloud: bool | None = None) -> str:
    """Top-level URL resolver. Applies cloud rename + /api prefix as needed."""
    cloud = is_cloud_host(base) if is_cloud is None else is_cloud
    if cloud:
        path = cloud_endpoint(path)
    return build_cloud_aware_url(base, path, force_cloud=cloud)


# =============================================================================
# API key resolution
# =============================================================================

def resolve_api_key(explicit: str | None) -> str | None:
    """Look up API key from CLI flag → env var. Strips whitespace and quotes."""
    val = explicit if explicit else os.environ.get(ENV_API_KEY)
    if val is None:
        return None
    val = val.strip().strip("'\"")
    return val or None


# =============================================================================
# HTTP transport
# =============================================================================

@dataclass
class HTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str  # final URL after redirects

    def text(self, encoding: str = "utf-8") -> str:
        return self.body.decode(encoding, errors="replace")

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8", errors="replace"))


def _sleep_backoff(attempt: int, base: float = RETRY_BASE_DELAY, cap: float = RETRY_MAX_DELAY) -> None:
    """Sleep with full-jitter exponential backoff."""
    delay = min(cap, base * (2 ** attempt))
    delay = random.uniform(0, delay)
    time.sleep(delay)


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    data: bytes | None = None,
    files: dict | None = None,
    form: dict | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    follow_redirects: bool = True,
    retries: int = DEFAULT_RETRIES,
    stream: bool = False,
    sink: Path | None = None,
) -> HTTPResponse:
    """Single entry point for all HTTP traffic.

    Behavior:
      - Retries on connection errors and on HTTP statuses in RETRY_STATUS_CODES,
        with exponential backoff + jitter.
      - For cross-host redirects, drops Authorization-style headers (so signed
        URLs don't leak the API key to S3/CloudFront).
      - When `stream=True` and `sink` is a Path, streams the response body to
        disk in 64 KiB chunks instead of buffering.

    Either `json_body`, `data`, or `files`+`form` may be supplied (mutually exclusive).
    """
    if headers is None:
        headers = {}
    headers = dict(headers)  # copy
    headers.setdefault("User-Agent", "hermes-comfyui-skill/5.0")

    if files or form is not None:
        # Multipart upload — needs `requests`. The stdlib fallback lacks
        # multipart encoding helpers; raise a clear error.
        if not HAS_REQUESTS:
            raise RuntimeError(
                "Multipart upload requires the `requests` package. "
                "Install with: pip install requests"
            )

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = _http_once(
                method=method, url=url, headers=headers,
                json_body=json_body, data=data, files=files, form=form,
                timeout=timeout, follow_redirects=follow_redirects,
                stream=stream, sink=sink,
            )
            if resp.status in RETRY_STATUS_CODES and attempt + 1 < retries:
                _sleep_backoff(attempt)
                continue
            return resp
        except (TimeoutError, ConnectionError, OSError) as e:
            last_exc = e
            if attempt + 1 < retries:
                _sleep_backoff(attempt)
                continue
            raise

    # Should not reach here unless retries was 0
    if last_exc:
        raise last_exc
    raise RuntimeError("http_request: retries exhausted with no response")


_SENSITIVE_HEADERS = ("x-api-key", "authorization", "cookie")


if HAS_REQUESTS:
    class _StripSensitiveOnRedirectSession(requests.Session):
        """Session that drops sensitive headers on cross-host redirects.

        `requests` already strips `Authorization` cross-host (rebuild_auth),
        but it does NOT strip custom headers like `X-API-Key`. We override
        `rebuild_auth` to additionally strip every header in
        `_SENSITIVE_HEADERS` when the destination is a different host —
        critical when ComfyUI Cloud's `/api/view` redirects to a signed S3 URL.
        """

        def rebuild_auth(self, prepared_request, response):  # type: ignore[override]
            super().rebuild_auth(prepared_request, response)
            try:
                old_url = response.request.url
                new_url = prepared_request.url
                old_host = (urlparse(old_url).hostname or "").lower()
                new_host = (urlparse(new_url).hostname or "").lower()
                if old_host and new_host and old_host != new_host:
                    headers = prepared_request.headers
                    for key in list(headers.keys()):
                        if key.lower() in _SENSITIVE_HEADERS:
                            del headers[key]
            except Exception:
                # Defensive: never let header stripping break a redirect.
                pass


def _http_once(
    *, method: str, url: str, headers: dict[str, str],
    json_body: Any, data: bytes | None, files: dict | None, form: dict | None,
    timeout: float, follow_redirects: bool,
    stream: bool, sink: Path | None,
) -> HTTPResponse:
    """One HTTP attempt. No retry."""
    if HAS_REQUESTS:
        kwargs: dict[str, Any] = {
            "method": method, "url": url, "headers": headers,
            "timeout": timeout, "allow_redirects": follow_redirects,
        }
        if json_body is not None:
            kwargs["json"] = json_body
        elif data is not None:
            kwargs["data"] = data
        elif files is not None or form is not None:
            kwargs["files"] = files
            kwargs["data"] = form
        if stream:
            kwargs["stream"] = True

        # Use the subclass that strips sensitive headers cross-host
        with _StripSensitiveOnRedirectSession() as s:
            try:
                r = s.request(**kwargs)
                if stream and sink is not None:
                    sink.parent.mkdir(parents=True, exist_ok=True)
                    with sink.open("wb") as f:
                        for chunk in r.iter_content(DOWNLOAD_CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                    body = b""  # already drained
                else:
                    body = r.content
                return HTTPResponse(
                    status=r.status_code,
                    headers={k: v for k, v in r.headers.items()},
                    body=body,
                    url=r.url,
                )
            except requests.exceptions.RequestException as e:
                # Convert to TimeoutError / ConnectionError so the retry loop
                # picks them up uniformly with the stdlib path.
                if isinstance(e, requests.exceptions.Timeout):
                    raise TimeoutError(str(e)) from e
                raise ConnectionError(str(e)) from e

    # ---------- stdlib fallback ----------
    if json_body is not None:
        body_bytes = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    else:
        body_bytes = data
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

    # urllib follows redirects by default. We need to:
    # 1) intercept cross-host redirects and drop X-API-Key
    # 2) optionally NOT follow redirects when follow_redirects=False
    class _RedirectHandler(urllib.request.HTTPRedirectHandler):
        def __init__(self, original_host: str, follow: bool):
            self.original_host = original_host
            self.follow = follow

        def redirect_request(self, req2, fp, code, msg, hdrs, newurl):
            if not self.follow:
                return None
            new_host = (urlparse(newurl).hostname or "").lower()
            if new_host != self.original_host:
                # Build a new request with cleaned headers
                clean_headers = {
                    k: v for k, v in req2.header_items()
                    if k.lower() not in {"x-api-key", "authorization", "cookie"}
                }
                new_req = urllib.request.Request(newurl, headers=clean_headers, method="GET")
                return new_req
            return super().redirect_request(req2, fp, code, msg, hdrs, newurl)

    original_host = (urlparse(url).hostname or "").lower()
    opener = urllib.request.build_opener(_RedirectHandler(original_host, follow_redirects))

    try:
        resp = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        return HTTPResponse(
            status=e.code,
            headers=dict(e.headers) if e.headers else {},
            body=e.read() or b"",
            url=getattr(e, "url", url),
        )

    final_url = resp.geturl()
    final_status = resp.status
    final_headers = dict(resp.headers)

    if stream and sink is not None:
        sink.parent.mkdir(parents=True, exist_ok=True)
        with sink.open("wb") as f:
            while True:
                chunk = resp.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
        return HTTPResponse(status=final_status, headers=final_headers, body=b"", url=final_url)

    return HTTPResponse(status=final_status, headers=final_headers, body=resp.read(), url=final_url)


def http_get(url: str, **kwargs: Any) -> HTTPResponse:
    return http_request("GET", url, **kwargs)


def http_post(url: str, **kwargs: Any) -> HTTPResponse:
    return http_request("POST", url, **kwargs)


def strip_meta_keys(workflow: dict) -> dict:
    """Drop top-level non-node keys (e.g. "_comment").

    Pitfall 0j: ComfyUI's validate_prompt iterates every top-level key as a
    node, so a bare string key 500s the submission ("Server got itself in
    trouble"). API-format nodes are always dicts; anything else is metadata.
    """
    return {k: v for k, v in workflow.items() if isinstance(v, dict)}


# =============================================================================
# Workflow validation & helpers
# =============================================================================

def is_api_format(workflow: Any) -> bool:
    """API format = top-level dict where each value has `class_type`."""
    if not isinstance(workflow, dict):
        return False
    if "nodes" in workflow and "links" in workflow:
        return False
    for v in workflow.values():
        if isinstance(v, dict) and "class_type" in v:
            return True
    return False


def unwrap_workflow(payload: Any) -> dict:
    """Unwrap common wrapper variants. Returns API-format workflow or raises ValueError."""
    if isinstance(payload, dict) and is_api_format(payload):
        return payload
    # Some files wrap workflow under "prompt" key (e.g. saved /prompt payloads)
    if isinstance(payload, dict) and "prompt" in payload and is_api_format(payload["prompt"]):
        return payload["prompt"]
    # Editor format
    if isinstance(payload, dict) and "nodes" in payload and "links" in payload:
        raise ValueError(
            "Workflow is in editor format (has top-level 'nodes' and 'links' arrays). "
            "Re-export from ComfyUI using 'Workflow → Export (API)' (newer UI) "
            "or 'Save (API Format)' (older UI)."
        )
    raise ValueError(
        "Workflow is not in API format. Each top-level entry must have a 'class_type' field."
    )


def is_link(value: Any) -> bool:
    """True if `value` is a [node_id, output_index] connection (length-2 list)."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


def iter_nodes(workflow: dict) -> Iterator[tuple[str, dict]]:
    """Yield (node_id, node) for each valid API-format node."""
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "class_type" in node:
            yield node_id, node


def iter_model_deps(workflow: dict) -> Iterator[dict]:
    """Yield {node_id, class_type, field, value, folder} for each model dependency."""
    for node_id, node in iter_nodes(workflow):
        cls = node["class_type"]
        if cls not in MODEL_LOADERS:
            continue
        inputs = node.get("inputs", {}) or {}
        for field_name, folder in MODEL_LOADERS[cls]:
            val = inputs.get(field_name)
            if val and isinstance(val, str) and not is_link(val):
                yield {
                    "node_id": node_id,
                    "class_type": cls,
                    "field": field_name,
                    "value": val,
                    "folder": folder,
                }


def iter_embedding_refs(workflow: dict) -> Iterator[tuple[str, str]]:
    """Yield (node_id, embedding_name) for every embedding mention in prompts."""
    for node_id, node in iter_nodes(workflow):
        inputs = node.get("inputs", {}) or {}
        for field_name, val in inputs.items():
            if field_name not in PROMPT_FIELDS:
                continue
            if not isinstance(val, str):
                continue
            for m in EMBEDDING_REGEX.finditer(val):
                yield node_id, m.group(1)


# =============================================================================
# Path safety
# =============================================================================

def safe_path_join(base: Path, *parts: str) -> Path:
    """Join paths, raising if the result escapes `base`.

    Server-supplied filenames may contain `../` etc. This guards against
    path-traversal attacks when downloading outputs.
    """
    base_resolved = base.resolve()
    candidate = base.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as e:
        raise ValueError(
            f"Refusing path traversal: {candidate} is outside {base_resolved}"
        ) from e
    return candidate


def media_type_from_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".mp4", ".webm", ".avi", ".mov", ".mkv", ".gif", ".webp"}:
        return "video"
    if ext in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}:
        return "audio"
    if ext in {".glb", ".obj", ".ply", ".gltf"}:
        return "3d"
    if ext in {".json", ".txt", ".md"}:
        return "text"
    return "image"


def looks_like_video_workflow(workflow: dict) -> bool:
    """Used to bump default timeout for video workflows."""
    for _, node in iter_nodes(workflow):
        if node["class_type"] in SLOW_OUTPUT_NODES:
            return True
        if node["class_type"].lower().startswith(("animatediff", "ade_", "wanvideo", "hunyuanvideo", "ltxvideo", "cogvideo")):
            return True
    return False


# =============================================================================
# Seed handling
# =============================================================================

# ComfyUI's max seed range. Many UIs treat `-1` as "randomize on submit".
SEED_MAX = 2**63 - 1
SEED_MIN = 0


def coerce_seed(value: Any) -> int:
    """Convert -1 or None to a fresh random seed; otherwise return int(value).

    Accepts numeric -1 OR string "-1" (both treated as "randomize"). Other
    parse failures raise TypeError/ValueError for the caller to surface.
    """
    if value is None:
        return random.randint(SEED_MIN, SEED_MAX)
    # Stringly-typed -1 from CLI / JSON should also randomize
    if isinstance(value, str) and value.strip() == "-1":
        return random.randint(SEED_MIN, SEED_MAX)
    if value == -1:
        return random.randint(SEED_MIN, SEED_MAX)
    return int(value)


# =============================================================================
# Cloud model-list normalization
# =============================================================================

def parse_model_list(payload: Any) -> set[str]:
    """Normalize model-list responses from local ComfyUI vs Comfy Cloud.

    Local: `["a.safetensors", "b.safetensors"]`
    Cloud: `[{"name": "a.safetensors", "pathIndex": 0}, ...]`
    """
    if not isinstance(payload, list):
        return set()
    out: set[str] = set()
    for item in payload:
        if isinstance(item, str):
            out.add(item)
        elif isinstance(item, dict):
            name = item.get("name") or item.get("filename") or item.get("path")
            if isinstance(name, str):
                out.add(name)
    return out


# =============================================================================
# Misc utilities
# =============================================================================

def new_client_id() -> str:
    return str(uuid.uuid4())


def fmt_kv(d: dict) -> str:
    """Pretty key=value for log lines."""
    return " ".join(f"{k}={v!r}" for k, v in d.items())


def emit_json(obj: Any, *, indent: int = 2) -> None:
    """Print JSON to stdout. Centralised so behavior can be tweaked (e.g., --raw)."""
    print(json.dumps(obj, indent=indent, default=str))


def log(msg: str) -> None:
    """stderr log with consistent prefix (so JSON stdout stays clean)."""
    print(f"[comfyui-skill] {msg}", file=sys.stderr)


# =============================================================================
# Gallery & output organization
#
# Every generation run (script download, and — via gallery.py --sweep — any
# server spool) ends up in the gallery, grouped by MONTH so a month's whole
# output is reviewable at scale in one folder:
#
#     <GALLERY_ROOT>/<YYYY-MM>/<slug>_<seed>_<NN>.<ext>
#
# with ONE manifest.json per month recording every run's prompt/seed/params/
# workflow plus each file's sha256. Filenames stay <slug>_<seed>_<NN> and get
# a numeric suffix only when a same-month run already produced that name.
# =============================================================================

# Canonical home for generated images. Override with $COMFY_GALLERY.
GALLERY_ROOT = Path(
    os.environ.get("COMFY_GALLERY", str(Path.home() / "Pictures" / "ComfyUI"))
).expanduser()

# Local server output spool that gallery.py sweeps by default. SaveImage on
# the single CLI install writes to <home>/ComfyUI/output. (Comfy Desktop's
# <home>/ComfyUI-Shared/output spool was retired with Desktop 2026-10-23.)
# Override with $COMFY_SPOOL_DIRS (colon-separated).
def _default_spool_dirs() -> list[str]:
    env = os.environ.get("COMFY_SPOOL_DIRS")
    if env:
        return [p for p in env.split(":") if p]
    home = Path.home()
    return [str(home / "ComfyUI" / "output")]


SERVER_OUTPUT_DIRS: tuple[Path, ...] = tuple(
    Path(p).expanduser() for p in _default_spool_dirs()
)

MANIFEST_SCHEMA = "comfyui-gallery/v1"

# Fields scanned for a human-readable prompt (order = preference).
PROMPT_KEYS = (
    "prompt", "positive", "text", "t5xxl", "clip_l",
    "text_g", "text_l", "refiner_prompt", "prompt_l",
)
SEED_KEYS = ("seed", "noise_seed")

_SLUG_BAD = re.compile(r"[^a-z0-9]+")
_SLUG_DASHES = re.compile(r"-{2,}")


def slugify(text: str, max_len: int = 48) -> str:
    """Lowercase hyphenated slug, <= max_len chars, never empty."""
    if not text:
        return "render"
    slug = _SLUG_BAD.sub("-", text.lower()).strip("-")
    slug = _SLUG_DASHES.sub("-", slug)
    if len(slug) > max_len:
        cut = slug[:max_len].rstrip("-")
        hyphen = cut.rfind("-")
        if hyphen > max_len // 2:
            cut = cut[:hyphen]
        slug = cut
    return slug or "render"


def prompt_from_args(args: dict) -> str | None:
    """First non-empty prompt-like string in an args dict (user --args)."""
    for k in PROMPT_KEYS:
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def prompt_slug(args: dict, *, fallback: str) -> str:
    p = prompt_from_args(args)
    return slugify(p) if p else slugify(fallback)


def find_seed_in_workflow(workflow: dict) -> int | None:
    """First literal numeric seed/noise_seed in any node input (post-injection).

    Returns None when the seed is a link (fixed elsewhere) or the workflow has
    no recognized seed field — callers then omit the seed from filenames.
    """
    for _, node in iter_nodes(workflow):
        inputs = node.get("inputs", {}) or {}
        for k in SEED_KEYS:
            v = inputs.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                return v
            if isinstance(v, str) and v.isdigit():
                return int(v)
    return None


def workflow_sha1(workflow: dict) -> str:
    """Stable fingerprint of the (post-injection) workflow for reproducibility."""
    import hashlib
    canonical = json.dumps(workflow, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gallery_month_dir(gallery: Path, now: Any = None) -> Path:
    """The month folder for a generation: <gallery>/<YYYY-MM>/.

    All of a month's output files assemble flat in this one folder (plus a
    merged manifest.json), so reviewing output at scale means opening a
    single folder per month instead of one folder per run. Creates the
    directory. Callers that only want to *preview* a location should build
    the Path themselves and avoid this helper.
    """
    from datetime import datetime as _dt
    now = now or _dt.now()
    month_dir = gallery / now.strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)
    return month_dir


def write_manifest(run_dir: Path, manifest: dict) -> Path:
    p = Path(run_dir) / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return p


# =============================================================================
# Human-readable PNG metadata (a `parameters` tEXt chunk)
#
# ComfyUI embeds the full API-format workflow in a `prompt` tEXt chunk — complete
# but not scannable. We add a flat `key: value` `parameters` chunk alongside it so
# the file alone tells you what made it, without parsing JSON. Written by
# finalize_downloads() (covers run_workflow.py / run_batch.py) and by gallery.py
# sweep for UI/MCP runs.
# =============================================================================

# Loader input keys → friendly label, in preference order (first non-empty wins).
_MODEL_KEYS = ("unet_name", "model_name", "ckpt_name", "checkpoint", "model")
_ENCODER_KEYS = ("clip_name", "text_encoder_name", "encoder_name")
_VAE_KEYS = ("vae_name",)
_REF_KEYS = ("image", "images")  # LoadImage filename inputs (string values only)
_NEG_KEYS = ("negative_prompt", "negative", "negative_text")
_SAMPLER_KEYS = ("sampler_name", "sampler")
_SCHED_KEYS = ("scheduler", "scheduler_name")
_SCALAR_KEYS = ("seed", "noise_seed", "steps", "cfg", "denoise", "width", "height", "resolution")


def _first_str(inputs: dict, keys: tuple) -> str | None:
    for k in keys:
        v = inputs.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def read_png_metadata(path: Path) -> dict[str, str]:
    """Return {keyword: text} for the tEXt/iTXt/zTXt chunks of a PNG.

    Self-contained copy of gallery.py's reader so _common.py (and anything that
    imports it) can read embedded ComfyUI metadata without a circular import.
    Empty dict on any error or non-PNG input.
    """
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return {}
    out: dict[str, str] = {}
    pos = 8
    n = len(data)
    while pos + 8 <= n:
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        try:
            if ctype == b"tEXt":
                key, _, val = body.partition(b"\x00")
                out[key.decode("latin-1")] = val.decode("latin-1")
            elif ctype == b"zTXt":
                key, _, comp = body.partition(b"\x00")
                out[key.decode("latin-1")] = zlib.decompress(comp).decode("latin-1")
            elif ctype == b"iTXt":
                key, rest = body.split(b"\x00", 1)
                if len(rest) >= 2:
                    flag, method = rest[0], rest[1]
                    rest2 = rest[2:]
                    lang_end = rest2.find(b"\x00")
                    if lang_end >= 0:
                        trans_end = rest2.find(b"\x00", lang_end + 1)
                        if trans_end >= 0:
                            text = rest2[trans_end + 1:]
                            if flag == 1 and method == 0:
                                text = zlib.decompress(text)
                            out[key.decode("latin-1")] = text.decode("utf-8", "replace")
        except Exception:
            continue
        if pos >= n:
            break
    return out


def render_human_params(workflow: dict) -> str:
    """Flatten an API-format workflow into a human-readable `key: value` block.

    Reads the same node inputs the gallery sweep already parses, but renders
    them as scannable lines (prompt first, then scalars, then model deps) so a
    PNG's `parameters` chunk reads like a recipe card. Multi-line values are
    collapsed to single lines. Returns an empty string when nothing is found.
    """
    prompt = ""
    negative = ""
    scalars: dict[str, Any] = {}
    sampler = scheduler = model = encoder = vae = None
    refs: list[str] = []
    for _, node in iter_nodes(workflow):
        inputs = node.get("inputs", {}) or {}
        for k in PROMPT_KEYS:
            v = inputs.get(k)
            if isinstance(v, str) and len(v) > len(prompt):
                prompt = v
        neg = _first_str(inputs, _NEG_KEYS)
        if neg and not negative:
            negative = neg
        for k in _SCALAR_KEYS:
            v = inputs.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)) and k not in scalars:
                scalars[k] = v
        if sampler is None:
            sampler = _first_str(inputs, _SAMPLER_KEYS)
        if scheduler is None:
            scheduler = _first_str(inputs, _SCHED_KEYS)
        if model is None:
            model = _first_str(inputs, _MODEL_KEYS)
        if encoder is None:
            encoder = _first_str(inputs, _ENCODER_KEYS)
        if vae is None:
            vae = _first_str(inputs, _VAE_KEYS)
        if node.get("class_type") == "LoadImage":
            for k in _REF_KEYS:
                v = inputs.get(k)
                if isinstance(v, str) and v.strip() and v not in refs:
                    refs.append(v.strip())

    def _one(v: Any) -> str:
        return " ".join(str(v).split())

    lines: list[str] = []
    if prompt:
        lines.append(f"prompt: {_one(prompt)}")
    if negative:
        lines.append(f"negative: {_one(negative)}")
    for k in ("seed", "noise_seed", "steps", "cfg", "denoise", "width", "height", "resolution"):
        if k in scalars:
            lines.append(f"{k}: {scalars[k]}")
    if sampler:
        lines.append(f"sampler: {sampler}")
    if scheduler:
        lines.append(f"scheduler: {scheduler}")
    if model:
        lines.append(f"model: {model}")
    if encoder:
        lines.append(f"text_encoder: {encoder}")
    if vae:
        lines.append(f"vae: {vae}")
    if refs:
        lines.append(f"references: {', '.join(refs)}")
    return "\n".join(lines)


def write_png_parameters(path: Path, text: str) -> bool:
    """Inject (or replace) a `parameters` tEXt chunk into a PNG, before IDAT.

    Idempotent: an existing `parameters` tEXt/iTXt chunk is stripped first, so
    re-running is safe. Returns True on success, False if the file isn't a
    readable PNG. Rewrites the file in place (atomic via temp + rename).
    """
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    # Walk chunks, dropping any existing `parameters` tEXt/iTXt chunk.
    pos = 8
    n = len(data)
    kept = bytearray()
    while pos + 8 <= n:
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos:pos + 12 + length]
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            body = data[pos + 8:pos + 8 + length]
            key = body.split(b"\x00", 1)[0]
            if key == b"parameters":
                pos += 12 + length
                continue
        kept += chunk
        pos += 12 + length
    # Build the new tEXt chunk: keyword\0text, CRC over type+data.
    payload = b"parameters\x00" + text.encode("latin-1", "replace")
    crc = zlib.crc32(b"tEXt" + payload) & 0xFFFFFFFF
    new_chunk = struct.pack(">I", len(payload)) + b"tEXt" + payload + struct.pack(">I", crc)
    # Insert right after IHDR (first chunk), before IDAT.
    ihdr_end = 8 + 8 + struct.unpack(">I", data[8:12])[0] + 4
    out = data[:ihdr_end] + bytes(new_chunk) + bytes(kept[ihdr_end - 8:])
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(out)
    tmp.replace(path)
    return True


def embed_human_params(path: Path, workflow: dict | None = None) -> str:
    """Write a human-readable `parameters` chunk into a PNG from its workflow.

    If ``workflow`` is omitted, it's read from the PNG's own embedded `prompt`
    chunk (so this works on any ComfyUI PNG, including UI/MCP runs). Returns the
    rendered text ("" if nothing to write or the file isn't a PNG).
    """
    path = Path(path)
    if workflow is None:
        try:
            meta = read_png_metadata(path)
        except Exception:
            meta = {}
        raw = meta.get("prompt", "")
        try:
            workflow = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            workflow = None
    if not isinstance(workflow, dict):
        return ""
    text = render_human_params(workflow)
    if text:
        write_png_parameters(path, text)
    return text


def finalize_downloads(
    downloaded: list[dict],
    *,
    run_dir: Path,
    slug: str,
    seed: int | None,
    prompt_id: str,
    workflow_ref: str,
    workflow_sha1: str,
    host: str,
    args: dict,
    warnings: list[str],
    rename: bool = True,
    source: str = "run",
) -> dict:
    """Rename downloaded files to <slug>[_<seed>]_<NN><ext> and merge the run
    into the month's manifest.

    - ``run_dir`` is the MONTH folder (<gallery>/<YYYY-MM>/). All of the
      month's files land flat in it; a name collision (two runs with the same
      slug+seed in one month) bumps NN until the name is free, so a month's
      whole output stays reviewable in one folder.
    - The on-disk ``run_dir/manifest.json`` is a MERGED month manifest: every
      run appends a record (source, prompt_id, slug, seed, params, workflow,
      files[]) under a per-file lock, so parallel batch runs can't clobber it.
    - Returns the RUN-level manifest dict (this run's files only) so callers
      report exactly what this run produced, not the whole month.

    Leaves are renamed IN PLACE (files were already downloaded into run_dir).
    Original server filenames are kept in the manifest under `source`. Every
    file entry carries its sha256 so gallery.py can dedupe spool copies.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict] = []
    for i, entry in enumerate(downloaded, start=1):
        path = Path(entry["file"])
        if rename:
            base = f"{slug}" + (f"_{seed}" if seed is not None else "")
            name = f"{base}_{i:02d}{path.suffix}"
            target = path.with_name(name)
            n = i
            while target.exists() and target.resolve() != path.resolve():
                n += 1
                target = path.with_name(f"{base}_{n:02d}{path.suffix}")
            if target != path:
                path.rename(target)
        else:
            target = path
        try:
            rel = target.resolve().relative_to(run_dir.resolve())
        except ValueError:
            rel = Path(target.name)
        files.append({
            "file": str(rel),
            "source": entry.get("filename") or path.name,
            "node_id": entry.get("node_id"),
            "type": entry.get("type") or media_type_from_filename(target.name),
            "subfolder": entry.get("subfolder", ""),
            "size": target.stat().st_size,
            "sha256": sha256_file(target),
        })
        if entry.get("seed") is not None:
            files[-1]["seed"] = entry["seed"]
        # Human-readable recipe card in the PNG itself (idempotent).
        if target.suffix.lower() == ".png":
            embed_human_params(target)
    now = datetime.now()
    run_manifest = {
        "schema": MANIFEST_SCHEMA,
        "source": source,
        "run_id": f"{now.strftime('%Y%m%d-%H%M%S')}-{slug[:24]}",
        "created_at": now.isoformat(timespec="seconds"),
        "prompt_id": prompt_id or None,
        "slug": slug,
        "seed": seed,
        "workflow": workflow_ref,
        "workflow_sha1": workflow_sha1,
        "host": host,
        "params": args or None,
        "warnings": warnings or None,
        "files": files,
    }
    merge_month_manifest(run_dir, run_manifest)
    return run_manifest


def merge_month_manifest(month_dir: Path, run_manifest: dict) -> Path:
    """Append a run record into <month_dir>/manifest.json under a file lock.

    The month manifest is the archive record for a whole month of generations:

        {schema, month, created_at, updated_at,
         runs: [ {run record incl. files[]}, ... ],
         files: [ flat file entries with slug/seed/sha256/run_id, ... ]}

    Read-modify-write is serialized with flock on the manifest file so
    run_batch's parallel workers can't corrupt it. Falls back to lock-free
    writes on platforms without fcntl. Returns the manifest path.
    """
    month_dir = Path(month_dir)
    month_dir.mkdir(parents=True, exist_ok=True)
    mpath = month_dir / "manifest.json"

    def _read() -> dict:
        try:
            raw = mpath.read_text(encoding="utf-8")
            parsed = json.loads(raw) if raw.strip() else {}
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _merge_into(data: dict) -> dict:
        now = datetime.now().isoformat(timespec="seconds")
        data.setdefault("schema", MANIFEST_SCHEMA)
        data["month"] = month_dir.name
        data["updated_at"] = now
        data.setdefault("created_at", now)
        runs = data.setdefault("runs", [])
        if not isinstance(runs, list):
            runs = data["runs"] = []
        runs.append(run_manifest)
        files = data.setdefault("files", [])
        if not isinstance(files, list):
            files = data["files"] = []
        for f in run_manifest.get("files", []) or []:
            files.append({
                "file": f.get("file"),
                "run_id": run_manifest.get("run_id"),
                "slug": run_manifest.get("slug"),
                "seed": f.get("seed", run_manifest.get("seed")),
                "prompt_id": run_manifest.get("prompt_id"),
                "type": f.get("type"),
                "size": f.get("size"),
                "sha256": f.get("sha256"),
            })
        return data

    try:
        import fcntl  # POSIX (macOS/Linux)
        with mpath.open("a+", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                raw = fh.read()
                try:
                    data = json.loads(raw) if raw.strip() else {}
                    if not isinstance(data, dict):
                        data = {}
                except Exception:
                    data = {}
                data = _merge_into(data)
                fh.seek(0)
                fh.truncate()
                fh.write(json.dumps(data, indent=2, default=str))
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    except (ImportError, OSError):
        # No fcntl (non-POSIX) — lock-free fallback.
        data = _read()
        data = _merge_into(data)
        mpath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return mpath
