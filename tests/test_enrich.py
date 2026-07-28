import asyncio
import config, enrich
def test_fallback_and_caption():
    result=asyncio.run(enrich.parse_caption("Аниме: Блич\nТрек: Неведомый трек"))
    assert result["anime"]=="Блич" and result["track"]=="Неведомый трек"
    caption=enrich.build_caption("Блич","трек")
    assert "Блич ⚔️" in caption and "тречок : трек" in caption
