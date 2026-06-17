from services.practice_validator import PracticeValidator
from engines.broker_engine.broker_engine import BrokerEngine


class PracticeService:

    def __init__(

        self,

        repository

    ):

        self.repository = repository

        self.validator = PracticeValidator()

        self.engine = BrokerEngine()

    def search(

        self,

        practice

    ):

        errors = self.validator.validate(

            practice

        )

        if len(errors):

            return {

                "success": False,

                "errors": errors,

                "response": None

            }

        response = self.engine.search(

            self.repository.all(),

            practice

        )

        return {

            "success": True,

            "errors": [],

            "response": response

        }