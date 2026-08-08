import asyncio
import config, enrich
def test_fallback_and_caption():
    result=asyncio.run(enrich.parse_caption("Аниме: Блич\nТрек: Неведомый трек"))
    assert result["anime"]=="Блич" and result["track"]=="Неведомый трек"
    caption=enrich.build_caption("Блич","трек")
    assert "Блич ⚔️" in caption and "тречок : трек" in caption
    assert '<a href="https://t.me/NosokVPNBot?start=partner_8235497168">Лучший VPN</a>' in caption


def test_client_initialization_failure_uses_fallback(monkeypatch):
    import openai

    monkeypatch.setattr(config, "ROUTERAI_API_KEY", "test-key")

    class BrokenClient:
        def __init__(self, **kwargs):
            raise TypeError("incompatible httpx")

    monkeypatch.setattr(openai, "AsyncOpenAI", BrokenClient)
    result = asyncio.run(enrich.parse_caption("Аниме: Блич\nТрек: Test"))
    assert result == {"anime": "Блич", "track": "Test", "ad": False}
