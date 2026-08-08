import hashlib, json, logging, random, re
import config
log = logging.getLogger("enrich")
SYSTEM = """Ты извлекаешь из подписи Telegram-поста название аниме и музыкального трека. Не придумывай. Верни строго JSON: {\"anime\": string|null, \"track\": string|null, \"ad\": boolean}. Удали хэштеги, ссылки и призывы подписаться."""
EMOJI_BY_KEYWORD = {"блич":"⚔️","bleach":"⚔️","наруто":"🍥","naruto":"🍥","ван пис":"🏴‍☠️","one piece":"🏴‍☠️","токийский гуль":"🩸","магическая битва":"👐","jujutsu":"👐","клинок":"🌊","demon slayer":"🌊","chainsaw":"🪚"}
def pick_emoji(anime: str | None) -> str:
    low = (anime or "").lower()
    for key, emoji in EMOJI_BY_KEYWORD.items():
        if key in low: return emoji
    return config.EMOJI_POOL[int(hashlib.sha256(low.encode()).hexdigest()[:8], 16) % len(config.EMOJI_POOL)] if anime else random.choice(config.EMOJI_POOL)
def _fallback_parse(text: str) -> dict:
    anime = track = None
    for line in (text or "").splitlines():
        if not anime and re.search(r"(аниме|anime)\s*[:\-—]", line, re.I): anime = re.split(r"[:\-—]", line, 1)[-1].strip() or None
        if not track and re.search(r"(трек|музык|песня|song|track|музло)\s*[:\-—]", line, re.I): track = re.split(r"[:\-—]", line, 1)[-1].strip() or None
    return {"anime": anime, "track": track, "ad": False}
async def parse_caption(text: str, file_name: str = "") -> dict:
    if not config.ROUTERAI_API_KEY: return _fallback_parse(text)
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.ROUTERAI_API_KEY, base_url=config.ROUTERAI_BASE_URL, timeout=30)
        user_content = f"Подпись:\n{text or '(пусто)'}\nИмя файла: {file_name or '(нет)'}"[:2000]
        response = await client.chat.completions.create(model=config.ROUTERAI_MODEL, temperature=0, response_format={"type":"json_object"}, messages=[{"role":"system","content":SYSTEM},{"role":"user","content":user_content}])
        data = json.loads(response.choices[0].message.content or "{}")
        return {"anime": data.get("anime") or None, "track": data.get("track") or None, "ad": bool(data.get("ad"))}
    except Exception as exc:
        log.warning("RouterAI parse failed: %s", exc)
        return _fallback_parse(text)
def build_caption(anime: str | None, track: str | None) -> str:
    lines = ([f"{anime} {pick_emoji(anime)}"] if anime else []) + ([f"тречок : {track}"] if track else [])
    return "\n".join(lines) + ("\n\n" if lines else "") + config.SIGNATURE
