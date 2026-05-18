class InterviewEngine:
    async def get_next_question(self, session_id: str) -> dict:
        raise NotImplementedError

    async def submit_answer(
        self, session_id: str, question_id: str, answer
    ) -> dict:
        raise NotImplementedError

    async def go_back(self, session_id: str) -> dict:
        raise NotImplementedError
