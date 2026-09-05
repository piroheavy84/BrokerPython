from enum import Enum


class RuleType(str, Enum):

    LTV = "LTV"

    LTC_EXCEPTION = "LTC_EXCEPTION"

    SPREAD = "SPREAD"

    RATE = "RATE"

    DURATION = "DURATION"

    AGE = "AGE"

    PURPOSE = "PURPOSE"

    PROPERTY = "PROPERTY"

    GREEN = "GREEN"

    CONSAP = "CONSAP"

    GUARANTEE = "GUARANTEE"

    DEROGATION = "DEROGATION"

    NOTE = "NOTE"
