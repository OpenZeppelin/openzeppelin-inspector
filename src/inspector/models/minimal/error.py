from dataclasses import dataclass


@dataclass
class Error:
    """
    A simple error container used for capturing and reporting error messages.

    Attributes:
        message: A human-readable error message.
    """

    message: str = ""

    def __json__(self) -> dict:
        """
        Convert the error to a JSON-serializable dictionary.

        Returns:
            A dictionary with the error message.
        """
        return {"message": self.message}
