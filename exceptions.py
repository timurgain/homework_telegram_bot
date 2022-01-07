class ForeignServerError(Exception):
    """Foreign server error."""

    pass


class HomeworksKeyNotFound(Exception):
    """Homeworks key not found into API response."""

    pass


class VerdictNotFound(Exception):
    """Verdict is not described."""

    pass
