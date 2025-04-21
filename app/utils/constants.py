import enum

API_KEY_HEADER="X-API-Key"
ADMIN_ACCESS_LEVEL=3
LIBRARIAN_ACCESS_LEVEL=2
USER_ACCESS_LEVEL=1




class BorrowingStatus(str, enum.Enum):
    BORROWED = "borrowed"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"
    DAMAGED = "damaged"


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"

    def __str__(self):
        return self.value