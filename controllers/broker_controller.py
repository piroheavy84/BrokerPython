from services.practice_service import PracticeService


class BrokerController:

    def __init__(

        self,

        repository

    ):

        self.service = PracticeService(

            repository

        )

    def search(

        self,

        practice

    ):

        return self.service.search(

            practice

        )