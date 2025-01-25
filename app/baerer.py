# from fastapi import Depends, HTTPException
# from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
#
# security = HTTPBearer()
#
#
# async def verify_token(
#         credentials: HTTPAuthorizationCredentials = Depends(security)
# ):
#     if (credentials.scheme != "Bearer" or
#             credentials.credentials != "тут токен"):
#         raise HTTPException(status_code=403,
#                             detail="Неверный или отсутствующий токен")
