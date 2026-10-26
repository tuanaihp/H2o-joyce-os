"""voice_clone.py - hồ sơ giọng nhân bản (clone once, reuse forever).

Mỗi giọng = một thư mục `<STATE_DIR>/voices/<slug>/` gồm `ref.wav` (mẫu gốc đã
chuẩn hoá) + `profile.json`. Backend hiện tại: v-tts (local, CPU, giấy phép
CC BY-NC - phi thương mại). Thiết kế thay backend được: khi cần bản thương mại
(ZeroTTS .npz / ElevenLabs voice_id) chỉ thêm backend mới, hồ sơ giữ nguyên.
"""
import asyncio
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import config as cfgmod
import winproc

_VOICES_ROOT = None
_VTTS = None          # singleton model (nạp nặng ~giây, tải weights ~285MB lần đầu)
_VTTS_LOCK = asyncio.Lock()
_FFMPEG = shutil.which("ffmpeg") or r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"


def voices_dir() -> Path:
    global _VOICES_ROOT
    if _VOICES_ROOT is None:
        _VOICES_ROOT = Path(cfgmod.STATE_DIR) / "voices"
        _VOICES_ROOT.mkdir(parents=True, exist_ok=True)
    return _VOICES_ROOT


def _slugify(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("đ", "d")
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s.strip())[:40].strip("-")
    return s or f"giong-{int(time.time())}"


def list_voices() -> list:
    out = []
    for d in sorted(voices_dir().iterdir() or []):
        p = d / "profile.json"
        if not (d.is_dir() and p.is_file() and (d / "ref.wav").is_file()):
            continue
        try:
            prof = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            prof = {}
        prof.setdefault("slug", d.name)
        out.append(prof)
    return out


def get_profile(slug: str) -> dict | None:
    slug = re.sub(r"[^\w-]", "", slug or "")
    d = voices_dir() / slug
    p = d / "profile.json"
    if p.is_file() and (d / "ref.wav").is_file():
        try:
            prof = json.loads(p.read_text(encoding="utf-8"))
            prof["slug"] = slug
            return prof
        except Exception:  # noqa: BLE001
            return None
    return None


def _to_wav(src: Path, dst: Path) -> bool:
    """Chuẩn hoá mẫu về wav 22050Hz mono bằng ffmpeg (v-tts đọc wav chuẩn)."""
    try:
        subprocess.run(
            [_FFMPEG, "-y", "-i", str(src), "-ac", "1", "-ar", "22050", str(dst)],
            capture_output=True, timeout=60, check=True, **winproc.kwargs_no_window())
        return dst.is_file() and dst.stat().st_size > 1000
    except Exception:  # noqa: BLE001
        return False


def save_voice(name: str, data: bytes, filename: str) -> dict:
    """Lưu mẫu giọng -> hồ sơ. Trả profile dict; raise ValueError khi audio hỏng."""
    slug = _slugify(name)
    d = voices_dir() / slug
    d.mkdir(parents=True, exist_ok=True)
    ext = Path(filename or "mau.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=str(d)) as tf:
        tf.write(data)
        tmp = Path(tf.name)
    try:
        ok = _to_wav(tmp, d / "ref.wav") if ext.lower() != ".wav" else False
        if not ok and ext.lower() == ".wav":
            shutil.copy2(str(tmp), d / "ref.wav")
            ok = True
        if not ok:
            shutil.rmtree(d, ignore_errors=True)
            raise ValueError("Không đổi được file audio - cần ffmpeg hoặc file .wav")
    finally:
        tmp.unlink(missing_ok=True)
    prof = {
        "slug": slug, "name": (name or slug).strip()[:60],
        "backend": "vtts",                      # đổi backend thương mại: "zerotts"/"elevenlabs"
        "license": "cc-by-nc",                  # v-tts = phi thương mại
        "created": int(time.time()),
        "source_file": filename or "",
    }
    (d / "profile.json").write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
    return prof


def delete_voice(slug: str) -> bool:
    slug = re.sub(r"[^\w-]", "", slug or "")
    d = voices_dir() / slug
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


def available() -> bool:
    try:
        import v_tts  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


async def _get_vtts():
    global _VTTS
    if _VTTS is not None:
        return _VTTS
    async with _VTTS_LOCK:
        if _VTTS is None:
            def _load():
                import v_tts.zeroshot as vz
                # Repo đổi tên v-tts -> valtec-tts; space weights mới vẫn public.
                vz.DEFAULT_ZEROSHOT_HF_REPO = "valtecAI-team/valtec-zeroshot-voice-cloning"
                cache = vz._get_cache_dir()
                model_dir = cache / vz.DEFAULT_ZEROSHOT_MODEL_NAME

                def _flatten_model():
                    # hf_hub_download giữ cấu trúc pretrained/zeroshot/; package mong ở root.
                    nested = model_dir / "pretrained" / "zeroshot"
                    if nested.exists():
                        for f in nested.iterdir():
                            dst = model_dir / f.name
                            if f.is_file() and not dst.exists():
                                shutil.copy2(f, dst)

                flat = (model_dir / "config.json").exists() and list(model_dir.glob("G_*.pth"))
                if not flat:
                    nested = model_dir / "pretrained" / "zeroshot"
                    if not nested.exists():
                        # Lần đầu tải weights ~285MB từ HF - có thể mất vài phút.
                        from huggingface_hub import hf_hub_download
                        model_dir.mkdir(parents=True, exist_ok=True)
                        for fname in ("G_175000.pth", "config.json"):
                            hf_hub_download(
                                repo_id=vz.DEFAULT_ZEROSHOT_HF_REPO,
                                filename=f"pretrained/zeroshot/{fname}",
                                local_dir=str(model_dir), repo_type="space",
                            )
                    _flatten_model()

                # SpeakerEncoder (trong src/) tìm hasp ở <cwd>/pretrained/hasp/.
                hasp_dst = Path("pretrained") / "hasp" / "pytorch_model.bin"
                if not hasp_dst.exists():
                    src = cache / "hasp" / "pretrained" / "hasp" / "pytorch_model.bin"
                    if not src.exists():
                        from huggingface_hub import hf_hub_download
                        src = Path(hf_hub_download(
                            repo_id="Edresson/Speaker_Encoder_H_ASP",
                            filename="pytorch_model.bin",
                            local_dir=str(cache / "hasp"),
                        ))
                    hasp_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, hasp_dst)

                # vinorm không chạy trên Windows/Py3.12+ (binary Linux + `import imp` đã
                # bị xoá). Stub TTSnorm tối thiểu: chuẩn hoá số sang chữ tiếng Việt qua
                # num2words (dep sẵn của v-tts), còn lại giữ nguyên.
                if "vinorm" not in sys.modules:
                    import types
                    def _ttsnorm(text, **_kw):
                        try:
                            from num2words import num2words
                            return re.sub(
                                r"\d+",
                                lambda m: num2words(int(m.group()), lang="vi"),
                                text,
                            )
                        except Exception:
                            return text
                    vinorm_stub = types.ModuleType("vinorm")
                    vinorm_stub.TTSnorm = _ttsnorm
                    vinorm_stub.__all__ = ["TTSnorm"]
                    # Spec rỗng để find_spec không raise; origin=None khiến bước
                    # "isolate vinorm" của phonemizer tự bỏ qua.
                    import importlib.machinery
                    vinorm_stub.__spec__ = importlib.machinery.ModuleSpec("vinorm", loader=None)
                    sys.modules["vinorm"] = vinorm_stub

                from v_tts import ZeroShotTTS
                ckpts = sorted(model_dir.glob("G_*.pth"))
                return ZeroShotTTS(
                    checkpoint_path=str(ckpts[-1]),
                    config_path=str(model_dir / "config.json"),
                    device="cpu",
                )
            _VTTS = await asyncio.to_thread(_load)
    return _VTTS


async def synthesize(text: str, slug: str) -> bytes:
    """Sinh audio wav giọng `slug`. Blocking CPU -> chạy trong thread."""
    prof = get_profile(slug)
    if not prof:
        raise ValueError(f"Không có hồ sơ giọng '{slug}'")
    if prof.get("backend", "vtts") != "vtts":
        raise ValueError(f"Backend '{prof.get('backend')}' chưa nối - đổi profile hoặc cài backend")
    tts = await _get_vtts()
    ref = str(voices_dir() / slug / "ref.wav")
    doc = text  # phien_am áp ở caller khi cần; giọng clone đọc text gốc cho tự nhiên

    def _run() -> bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
            out = tf.name
        try:
            tts.clone_voice(text=doc, reference_audio=ref, output_path=out)
            return Path(out).read_bytes()
        finally:
            Path(out).unlink(missing_ok=True)

    audio = await asyncio.to_thread(_run)
    if not audio:
        raise RuntimeError("v-tts trả audio rỗng")
    return audio
