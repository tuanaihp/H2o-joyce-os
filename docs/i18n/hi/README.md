<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### बदलने योग्य दिमाग वाला agentic AI + Second Brain - आपके चुने मॉडल पर चलता है (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), आवाज़, नॉलेज ग्राफ़ और रोज़ खुद समझदार होता है।

<!-- flags:start -->
<p align="center">
<b>🌐 12 भाषाओं में उपलब्ध</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी">
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · 🇮🇳 **हिन्दी** · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 यह README का मशीनी अनुवाद है। Joyce उसी भाषा में जवाब देता है जिसमें आप लिखते हैं; इंटरफ़ेस वर्तमान में वियतनामी और अंग्रेज़ी में है। पूरा दस्तावेज़ [docs/en](../../../docs/en/README.md) में है। सुधारों का स्वागत है ([CONTRIBUTING](../../../CONTRIBUTING.en.md))।

## अपने ही AI से त्वरित इंस्टॉल

इस रिपो का लिंक अपनी मशीन पर चल रहे **Claude Code** या **Codex** को देकर कहें «Joyce OS इंस्टॉल करो»। बस एक कमांड (Windows पर `powershell -ExecutionPolicy Bypass -File install.ps1`, Linux/macOS पर `chmod +x install.sh && ./install.sh`) Python व डिपेंडेंसी, सब्सक्रिप्शन वाले चार CLI ब्रेन (`claude`, `codex`, `agy`, `grok`), `.env` सब कुछ इंस्टॉल करके `http://localhost:7777` पर सर्वर चला देती है। फिर डैशबोर्ड के **Models** पेज से हर ब्रेन में लॉगिन करें।

## Joyce क्या है?

Joyce OS कोई चैटबॉट नहीं, बल्कि आपकी मशीन/VPS पर चलने वाला सेल्फ-होस्टेड agentic AI है: फ़ाइलें पढ़ता/लिखता है, टूल (MCP) बुलाता है, skills चलाता है, बैकग्राउंड काम सौंपता है, रिमाइंडर बनाता है - सब एक सुंदर, आवाज़-नियंत्रित डैशबोर्ड में, साथ में **Second Brain** (मेमोरी + wiki) जो समय के साथ ज्ञान जमा करता है। दस ब्रेन उपलब्ध: सब्सक्रिप्शन वाले Claude Code, ChatGPT/Codex, Grok Build, Antigravity CLI और सिर्फ API key वाले OpenRouter, OpenAI, Google Gemini, Anthropic, Groq, Ollama Cloud। क्षमता Joyce में है, मॉडल में नहीं।

## ✨ प्रमुख विशेषताएँ

प्रमुख विशेषताएँ: हैंड्स-फ्री वॉइस चैट, ऑफ़लाइन नॉलेज ग्राफ़, फ़ुल-टेक्स्ट सेशन खोज, `.md`/`.txt` सीधे एडिट करने वाला फ़ाइल मैनेजर, ग्रुप्ड व टॉगलेबल Skills, हर इंजन को नेटिव टूल देने वाले Plugins (एक Python फ़ोल्डर), अपनी मेमोरी वाले Agents और मल्टी-स्टेप Workflows, बैकग्राउंड loops व रिमाइंडर्स, AI-चलित Kanban, हर बातचीत के बाद सेल्फ-लर्निंग (एक टैप में अनडू), मल्टी-अकाउंट कनेक्शन स्टोर (POS, Zalo, Ads, Google Workspace…), Telegram व Zalo चैनल, आपके ChatGPT प्लान से इमेज जनरेशन, दिन/प्रोवाइडर वार उपयोग पेज, GitHub पर ब्रेन बैकअप, बिना फ़ीचर खोए इंजन स्विच, और पब्लिक डिप्लॉय पर लॉगिन अनिवार्य व एन्क्रिप्टेड सीक्रेट्स।

## 🚀 इंस्टॉलेशन

तीन रास्ते: Hostinger Docker Manager (`DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD` से डोमेन + HTTPS), किसी भी VPS पर `docker compose up -d` (`http://<ip>:7777`), या Windows पर सीधे `setup.bat`/`start-joyce.bat`। पब्लिक रन पर Joyce लॉगिन अनिवार्य करता है; env से admin पहले से बनाएँ और बाद में 2FA (TOTP) चालू करें।

## 🎬 पहली बार सेटअप

पहली बार खोलने पर सेटअप विज़ार्ड चलाता है: 1) admin अकाउंट (पब्लिक पर ज़रूरी); 2) ब्रेन चुनें - सब्सक्रिप्शन में एक बार लॉगिन, API key में बस key चिपकाएँ; 3) मॉडल चुनें - Models पेज से कभी भी बदलें, कोई फ़ीचर नहीं जाता; 4) चाहें तो कनेक्शन (POS, विज्ञापन, कैलेंडर, Zalo…) जोड़ें ताकि रिपोर्ट असली नंबरों पर आए।

## 📖 उपयोग मार्गदर्शिका

बाईं नेव बार **31 पेज** को 7 समूहों में बाँटती है: ब्रेन (ग्राफ़/चैट/फ़ाइलें/सेल्फ-लर्निंग), Code (असली टर्मिनल), क्षमताएँ (Agents/Skills/Workflows/Plugins/Chatbot/इनबॉक्स), काम (Kanban/अनुसूचित), कनेक्शन (स्टोर/चैनल/Models), सिस्टम (उपयोग/सेटिंग/मैस्कॉट/अपडेट/अकाउंट)। पूरा विषय-सूची: [docs/README.md](../../../docs/README.md); अंग्रेज़ी में [docs/en/](../../../docs/en/README.md)।

## ⚙️ कॉन्फ़िगरेशन (`.env`)

सब खाली छोड़ें तो भी चलता है: `env.example` को `.env` में कॉपी करें और ज़रूरी वेरिएबल जोड़ें। मुख्य: `JOYCE_HOST`/`JOYCE_PORT` (डिफ़ॉल्ट 127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`। पूरा विवरण `docs/16-cau-hinh-env.md` में।

## 🔐 सुरक्षा

पब्लिक रन पर लॉगिन अनिवार्य, लॉगिन रेट-लिमिट, राइट रिक्वेस्ट पर Origin जाँच से CSRF रोक, `settings.json` में सीक्रेट्स एन्क्रिप्टेड (मशीन की `JOYCE_STATE_DIR/.secret_key`), 30-दिन सेशन एक्सपायरी, और यूज़र-इंस्टॉल प्लगइन डिफ़ॉल्ट बंद (`JOYCE_ENABLE_USER_PLUGINS=true` से चालू)। रिमोट एक्सेस HTTPS से करें।

## 🔄 अपडेट

लोकल में `git push` करते ही CI, GHCR पर नया इमेज बनाता है; VPS पर `./update.sh` पुल करके रीस्टार्ट करता है (डेटा वॉल्यूम में सुरक्षित)। ऐप का अपडेट पेज वन-टैप अपडेट और रोलबैक देता है जहाँ सपोर्ट हो।

## 🌐 दूरस्थ एक्सेस (Hostinger से अलग VPS)

Hostinger से अलग VPS पर Cloudflare Tunnel: `docker compose --profile tunnel up -d`, फिर `docker compose logs tunnel | grep trycloudflare` से `https://xxx.trycloudflare.com` लें।

## 🏗️ आर्किटेक्चर

ब्राउज़र (वॉइस + ग्राफ़), Telegram, Zalo MCP सब FastAPI (`server/`) + MCP Hub (सभी इंजनों का साझा कनेक्शन स्टोर) + Second Brain (markdown वॉल्ट) में मिलते हैं। बैकएंड शुद्ध Python FastAPI; फ्रंटएंड बिना फ्रेमवर्क HTML/CSS/JS (`dashboard/`), VPS पर हल्का।

## 🩺 समस्या निवारण

कोड बदलने पर असर न दिखे तो सर्वर रीस्टार्ट करें; पोर्ट अधूत हो तो पुराना प्रोसेस मारें; Hostinger इमेज न खींचे तो GHCR पैकेज Public करें; ब्रेन लॉगिन माँगे तो Models पेज से लॉगिन करें; पुरानी चैट में ग्रे इमेज बॉक्स `attachments/` कैश एक्सपायर है, सामान्य है।

## 📂 रिपॉज़िटरी संरचना

`server/` बैकएंड, `dashboard/` फ्रंटएंड (`i18n/` हर भाषा का JSON शब्दकोश), `brains/` सभी second brains, `system/` बंडल प्लगइन व कनेक्शन टेम्पलेट, `tests/`, `docs/` व `docs/en/` दस्तावेज़, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`।

## 🙏 प्रेरणा और आभार

आभार: Claude Code व Claude Agent SDK (Anthropic), Codex CLI (OpenAI), OpenRouter/OpenAI/Gemini/Anthropic/Groq की APIs, Model Context Protocol मानक (पूरा कनेक्शन स्टोर इसी पर), और Second Brain + Bullet Journal डिजिटल पैटर्न।

## 📄 लाइसेंस

**MIT** लाइसेंस के साथ ओपन सोर्स - स्वतंत्र रूप से उपयोग, संशोधन, वितरण; बस श्रेय पंक्ति रखें। देखें [LICENSE](../../../LICENSE)।

## ☕ Joyce OS को समर्थन दें

Joyce OS मुफ़्त ओपन-सोर्स है; अकेला डेवलपर कोड और टेस्ट सर्वर खर्च उठाता है। अगर यह आपके काम या जीवन में मदद करता है तो छोटा सा समर्थन बग फ़िक्स और नई सुविधाओं के लिए समय देता है।
