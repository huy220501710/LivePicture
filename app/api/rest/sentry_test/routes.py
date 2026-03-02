from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/sentry-test", tags=["sentry-test"])


@router.get("/sentry-debug")
async def trigger_zero_division():
    """Artificial zero division error"""
    division_by_zero = 1 / 0
    return {"result": division_by_zero}


@router.get("/sentry-http-exception")
async def trigger_http_exception():
    """Искусственное возбуждение HTTPException"""
    raise HTTPException(
        status_code=status.HTTP_418_IM_A_TEAPOT,
        detail="I'm a teapot - test HTTPException error",
    )


@router.get("/sentry-index-error")
async def trigger_index_error():
    """Artificial index out of range error"""
    data = [1, 2, 3]
    return {"result": data[5]}  # IndexError


@router.get("/sentry-key-error")
async def trigger_key_error():
    """Artificial missing key in dictionary error"""
    data = {"a": 1, "b": 2}
    return {"result": data["c"]}  # KeyError


@router.get("/sentry-custom-error")
async def trigger_custom_exception():
    """Artificial custom error"""

    class CustomError(Exception):
        pass

    raise CustomError("This is a custom error for Sentry testing")
