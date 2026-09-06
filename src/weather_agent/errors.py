class WeatherServiceError(Exception):
    """Base error for failures while obtaining or parsing weather data."""


class WeatherServiceUnavailable(WeatherServiceError):
    """The remote weather service could not provide a response."""


class WeatherDataInvalid(WeatherServiceError):
    """The provider response did not contain usable weather data."""


class LanguageModelError(Exception):
    """The configured language model could not process the request."""


class ConfigurationError(Exception):
    """Required application configuration is missing or invalid."""
