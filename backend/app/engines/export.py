class ExportEngine:
    async def generate(
        self, workspace_id: str, financial_year: str, password: str
    ) -> str:
        raise NotImplementedError

    async def get_status(self, export_id: str) -> dict:
        raise NotImplementedError
