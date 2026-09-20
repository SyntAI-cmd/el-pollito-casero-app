class ErrorDominio(Exception):
    """Regla de negocio violada. El router la traduce a HTTP 422; nunca es un bug."""
