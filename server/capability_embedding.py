"""capability_embedding.py - Nhánh 'semantic' THẬT cho capability_resolver.

Móc `embedding` của resolver tồn tại từ lâu nhưng `get_resolver()` chưa bao giờ
truyền adapter vào - nhánh semantic chỉ hiện trong report dưới dạng số 0. File
này đấu nhánh đó bằng đường KHIÊM TỐN nhất có thể: không vector DB, không model
embedding riêng, không thêm cơ sở hạ tầng.

Cơ chế (mượn ý tưởng prompts.chat `embeddings.ts` - dịch query trước khi khớp):
lỗ hổng thật là NGÔN NGỮ, không phải vector. Tool tên `create_invoice` trong
khi người dùng hỏi "chốt đơn cho khách" - lexical FTS5 trượt vì không chung một
từ nào. Một model rẻ đã cấu hình dịch query sang English keywords, rồi adapter
chạy lại ĐÚNG `registry.search` trên bản dịch: capability mà query gốc không
chạm từ nào giờ lọt vào ứng viên. Phần xếp hạng vẫn do fusion của resolver lo
(RRF + trần SEMANTIC_INFLUENCE) - adapter chỉ trả THỨ TỰ ứng viên, không tự
chấm điểm, và hard filter của resolver chạy sau nên không bao giờ nới quyền.

An toàn tuyệt đối: mọi lỗi - chưa cấu hình provider API nào, timeout, model trả
rác - đều trả [], tức resolver chạy lexical thuần đúng như hôm qua. Cuộc gọi
dịch là SYNC urllib (vài trăm ms, timeout 5s) vì resolve() chạy sync; cache hai
tầng (query->bản dịch, (query,brain,revision)->ids) nên registry đổi thì cache
tự vô hiệu và query lặp không tốn thêm lượt model.

Vì sao chưa làm vector thật: cần một provider embed + index lưu trữ + invalidation
theo revision - đường đó đi qua đúng protocol `search()` ở đây nên thay ruột sau
này không đụng resolver. Nhánh dịch-query đã khâu phần lớn lỗ hổng thực tế.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import OrderedDict

_IDS_CACHE: OrderedDict = OrderedDict()    # (query_norm, brain, revision) -> [capability_id]
_TR_CACHE: OrderedDict = OrderedDict()     # query_norm -> (ts, english)
_TR_NEG_TTL = 600.0                        # dịch thất bại: không thử lại trong 10 phút
_CACHE_MAX = 512
_TIMEOUT_S = 5.0
_MAX_TOKENS = 48

_PROMPT = (
    "Rewrite the user's request as English search keywords for matching software "
    "tools or capabilities. Output ONLY the keywords, one line, lowercase, no "
    "punctuation, no explanation. Keep proper nouns. If already English, echo it."
)

# Thứ tự quét khi spec việc nền của chủ KHÔNG phải provider API (vd đang dùng CLI):
# ưu tiên nhà nhanh/rẻ vì đây là lượt phụ trong đường nóng của resolver. "zai"
# đứng đầu: glm-4.7-flash FREE vĩnh viễn ($0) nên lượt dịch không đốt tiền chủ.
_SCAN_ORDER = ("zai", "groq", "deepseek", "gemini", "openrouter", "openai")

_DEFAULT_MODELS = {
    "zai": "glm-4.7-flash",
    "groq": "llama-3.3-70b-versatile",
    "deepseek": "deepseek-flash",
    "gemini": "gemini-2.5-flash",
    "openrouter": "openai/gpt-4o-mini",
    "openai": "gpt-4o-mini",
}


def _urls():
    """{provider: url_chat_completions} - lazy vì engine.py nặng và vài URL dựng
    từ settings (ollama-local, openai-compat)."""
    import engine as eng
    return {
        "zai": eng.ZAI_URL,
        "groq": eng.GROQ_URL,
        "deepseek": eng.DEEPSEEK_URL,
        "gemini": eng.GEMINI_URL,
        "openrouter": eng.OPENROUTER_URL,
        "openai": eng.OPENAI_URL,
        "ollama": eng.OLLAMA_URL,
        "ollama-local": eng.ollama_local_url(),
        "openai-compat": eng.openai_compat_url(),
    }


def _resolve_target(settings) -> tuple:
    """(url, api_key, model) cho lượt dịch, hoặc ("", "", "") khi không có provider
    nào dùng được. Ưu tiên ĐÚNG model việc nền chủ đã chọn (spec_for_tag) nếu nó là
    provider API - chủ đã kiểm nó chạy được cho việc nền; không phải thì quét các
    provider có key với model mặc định an toàn."""
    try:
        import config as cfgmod
        import task_router
        import aux_engine

        s = settings if settings is not None else cfgmod.read_settings()
        urls = _urls()
        sp = task_router.spec_for_tag("", s)
        prov = (sp.get("provider") or "").strip()
        model_spec = (sp.get("model") or "").strip()

        if prov in urls and prov != "anthropic-api":
            url = urls[prov]
            key = "none" if prov in ("ollama-local",) else (
                aux_engine.api_key_for(prov, s) or ("none" if prov == "openai-compat" else ""))
            model = model_spec or _DEFAULT_MODELS.get(prov, "")
            # ollama/openai-compat/ollama-local không có default model an toàn - chỉ dùng
            # khi spec khai model; openai-compat còn cần có url thì mới tính.
            if url and key and (model or prov not in ("ollama", "openai-compat", "ollama-local")):
                if model:
                    return url, key, model

        for p in _SCAN_ORDER:
            key = aux_engine.api_key_for(p, s)
            if key:
                return urls[p], key, _DEFAULT_MODELS[p]
    except Exception:
        pass
    return "", "", ""


def _post_chat(url: str, api_key: str, model: str, text: str) -> str:
    """Một lượt chat/completions sync. Trả "" khi lỗi - caller coi như không dịch được."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if "openrouter.ai" in url:
        headers.update({"HTTP-Referer": "http://localhost:7777", "X-Title": "Joyce OS"})
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": text},
        ],
        "max_tokens": _MAX_TOKENS,
        "temperature": 0,
        "stream": False,
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    except Exception:
        return ""


def _put(cache: OrderedDict, key, value):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > _CACHE_MAX:
        cache.popitem(last=False)


def translate(query: str) -> str:
    """Query -> English keywords qua model rẻ đã cấu hình. "" khi không dịch được
    hoặc không có provider. Cache kết quả lẫn thất bại (TTL ngắn) để một provider
    sập không làm mỗi query tốn một timeout."""
    qn = str(query or "").strip().casefold()
    if not qn:
        return ""
    hit = _TR_CACHE.get(qn)
    if hit is not None:
        ts, cached = hit
        if cached or (time.time() - ts) < _TR_NEG_TTL:
            _TR_CACHE.move_to_end(qn)
            return cached
    url, key, model = _resolve_target(None)
    en = _post_chat(url, key, model, query) if url else ""
    # Giữ chữ thường + cắt đúng dòng đầu - model đôi khi kèm dòng giải thích.
    en = " ".join(en.splitlines()[:1]).strip()[:300]
    _put(_TR_CACHE, qn, (time.time(), en))
    return en


class TranslatedLexicalAdapter:
    """EmbeddingAdapter cho resolver: search(query) = registry.search(query_đã_dịch).

    `translate_fn` tiêm được để test chạy không cần provider thật.
    """

    def __init__(self, registry=None, translate_fn=None):
        self._registry = registry
        self._translate = translate_fn or translate

    def _reg(self):
        if self._registry is not None:
            return self._registry
        from capability_registry import get_registry
        return get_registry()

    def translate_query(self, query: str) -> str:
        """Query đã dịch (tiếng Anh) - resolver dùng để chấm ứng viên semantic theo
        ý nghĩa chứ không theo chữ gốc. "" khi không dịch được."""
        try:
            return str(self._translate(str(query or "")) or "")
        except Exception:
            return ""

    def search(self, query: str, brain: str, limit: int) -> list:
        """[(capability_id, score)] theo thứ tự FTS của bản dịch. Resolver chỉ dùng
        THỨ TỰ (RRF) nên score ở đây chỉ mang tính giữ chỗ."""
        q = str(query or "").strip()
        if not q:
            return []
        reg = self._reg()
        try:
            rev = reg.revision(brain)
        except Exception:
            rev = 0
        key = (q.casefold(), str(brain), rev)
        if key in _IDS_CACHE:
            _IDS_CACHE.move_to_end(key)
            return [(c, 1.0) for c in _IDS_CACHE[key]]

        ids = []
        try:
            en = self._translate(q)
        except Exception:
            en = ""
        if en and en.casefold() != q.casefold():
            seen = set()
            for item in reg.search(en, brain, limit):
                cid = str(item.get("capability_id") or "")
                if cid and cid not in seen:
                    seen.add(cid)
                    ids.append(cid)
                    if len(ids) >= int(limit or 80):
                        break
        _put(_IDS_CACHE, key, ids)
        return [(c, 1.0) for c in ids]


_ADAPTER: TranslatedLexicalAdapter | None = None


def get_adapter() -> TranslatedLexicalAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = TranslatedLexicalAdapter()
    return _ADAPTER


def reset_caches():
    """Test hook: xoá cache để mỗi ca chạy độc lập."""
    _IDS_CACHE.clear()
    _TR_CACHE.clear()
