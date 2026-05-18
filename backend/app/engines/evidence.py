class EvidenceEngine:
    async def process_upload(
        self, workspace_id: str, file_data: bytes, filename: str
    ) -> dict:
        raise NotImplementedError
