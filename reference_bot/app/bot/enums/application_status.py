from enum import Enum


class ApplicationStatus(Enum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    CANCELED = "canceled"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    # Старые статусы для совместимости
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    STAGE_3 = "stage_3"
    APPROVED = "approved"
