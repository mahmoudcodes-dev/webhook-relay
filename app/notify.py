import httpx


class TelegramNotifier:
    """Sends formatted messages to a Telegram chat via the Bot API."""

    def __init__(self, bot_token: str, chat_id: str, transport: httpx.BaseTransport | None = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._client = httpx.AsyncClient(transport=transport, timeout=10.0)

    async def send(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            r = await self._client.post(url, json={"chat_id": self.chat_id, "text": text})
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
