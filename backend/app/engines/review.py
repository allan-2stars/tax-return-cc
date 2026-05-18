class ReviewEngine:
    async def get_queue(self, workspace_id: str) -> list:
        raise NotImplementedError

    async def take_action(
        self, item_id: str, action: str, payload: dict
    ) -> dict:
        raise NotImplementedError
