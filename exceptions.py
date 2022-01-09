class ForeignServerError(Exception):
    """Foreign server error."""

    pass


class TelegramError(Exception):
    """Telegram server error."""

    pass


class TokenAvailabilityError(Exception):
    """Token is not available."""

    pass


class HomeworkNameKeyNotFound(Exception):
    """Homeworks key not found into API response."""

    pass


class HomeworkStatusKeyNotFound(Exception):
    """Homeworks key not found into API response."""

    pass


class HomeworksKeyNotFound(Exception):
    """Homeworks key not found into API response."""

    pass


class HomeworksIsNotList(Exception):
    """Homeworks value is not list type into API response."""

    pass


class ResponseTextIsNotDict(Exception):
    """Response.text is not dict type into API response."""

    pass


class HomeworkIsNotDict(Exception):
    """Response.text is not dict type into API response."""

    pass


class VerdictNotFound(Exception):
    """Verdict is not described."""

    pass
