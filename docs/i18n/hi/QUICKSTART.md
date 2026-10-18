<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · **हिन्दी** · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## विकल्प 1 - Hostinger VPS (Docker Manager, एक क्लिक)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, बंडल में मौजूद `docker-compose.hostinger.yml` चिपकाएँ; HTTPS + डोमेन के लिए **Environment** में `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` डालें। **Deploy**, 1-3 मिनट प्रतीक्षा करें, ऐप खोलें। पहली बार admin अकाउंट बनाने को कहेगा, और कंटेनर टर्मिनल में Claude Code में एक बार लॉगिन: `claude auth login --claudeai`। अपडेट: Docker Manager में **Redeploy**।

## विकल्प 2 - किसी भी मशीन या VPS पर Docker

Docker वाली किसी भी मशीन पर `docker compose -f docker-compose.yml up -d`, फिर http://localhost:7777 खोलें। Caddy से HTTPS चाहिए तो `-f docker-compose.https.yml` जोड़ें।

## विकल्प 3 - सीधे चलाएँ (Windows, बिना Docker)

Python 3.12 + Node 22 इंस्टॉल करें, प्रोजेक्ट फ़ोल्डर में `setup.bat` एक बार चलाएँ (.venv बनाता है, डिपेंडेंसी और दो CLI इंजन डालता है), `start-joyce.bat` से बैकग्राउंड में चलाएँ (`stop-joyce.bat` से बंद), http://localhost:7777 खोलें।

## चलने के बाद

**Models** पेज से इंजन/मॉडल चुनें; **Connections** में कनेक्शन जोड़ें (POS, विज्ञापन, कैलेंडर, Zalo…) ताकि रिपोर्ट असली नंबरों पर चले; brain को GitHub पर बैकअप करें; **Usage** पेज से टोकन खर्च देखें।

## पूरा दस्तावेज़

देखें [docs/README.md](../../../docs/README.md) - हर फ़ीचर की गाइड; अंग्रेज़ी अनुवाद [docs/en/](../../../docs/en/README.md) में।

## आम समस्याएँ

Hostinger पर ऐप का अपडेट बटन काम न करना डिज़ाइन है - Docker Manager में **Redeploy** इस्तेमाल करें; ChatGPT/Codex «model not supported» बोले तो Models पेज पर सही Codex मॉडल चुनें; और अधिक `docs/17` में।
