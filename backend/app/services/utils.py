from fastapi import HTTPException, status
from functools import wraps
from typing import Optional
import logging

logger = logging.getLogger(__name__)

#router error handler + logging
def handle_route_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Route failed: %s", func.__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    return wrapper


#class code normalizer for course find and study group find
def normalize_code(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    return value.strip().replace(" ", "").upper()