from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import SecurityScopes, HTTPAuthorizationCredentials, HTTPBearer
from .config import get_settings
from supabase import Client, create_client
import http.client


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )


class DBConnectionError(HTTPException):
    def __init__(self, detail: str, **kwargs):
        super().__init__(
            status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=detail
        )


class VerifyToken:
    def __init__(self):
        self.config = get_settings()

        # This gets the JWKS from a given URL and does processing, so you can
        # use any of the keys available
        jwks_url = f'https://{self.config.auth0_domain}/.well-known/jwks.json'
        self.jwks_client = jwt.PyJWKClient(jwks_url)

    async def verify(self,
                     security_scopes: SecurityScopes,
                     token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer())
                     ):
        if token is None:
            raise UnauthenticatedException

        # This gets the 'kid' from the passed token
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token.credentials).key
        except jwt.exceptions.PyJWKClientError as error:
            raise UnauthorizedException(str(error))
        except jwt.exceptions.DecodeError as error:
            raise UnauthorizedException(str(error))

        try:
            payload = jwt.decode(
                token.credentials,
                signing_key,
                algorithms=self.config.auth0_algorithms,
                audience=self.config.auth0_api_audience,
            )
        except Exception as error:
            raise UnauthorizedException(str(error))

        return payload

    # TODO: Testear
    async def register_owner(self, userID):
        conn = http.client.HTTPSConnection("")

        # Ver si es necesario sacarle el hardcode al rol id
        payload = "{ \"roles\": [ \"rol_xGUgBNgqN8t4RijP\", \"rol_xGUgBNgqN8t4RijP\" ] }"

        headers = {
            'content-type': "application/json",
            'authorization': "Bearer " + self.config.auth0_management_token,
            'cache-control': "no-cache"
        }

        conn.request("POST", "/" + self.config.auth0_domain + "/api/v2/users/" + userID + "/roles", payload, headers)

        res = conn.getresponse()
        data = res.read()

        print(data.decode("utf-8"))


# Código para conectarme a la DB
class Connect:
    def __init__(self):
        self.config = get_settings()

    def connect(self):
        supabase: Client = create_client(self.config.supabase_url, self.config.supabase_key)
        try:
            # Cambiar esto luego con el usuario y contraseña que corresponda
            data = supabase.auth.sign_in_with_password(
                {"email": self.config.api_email, "password": self.config.api_password})
        except Exception as error:
            raise DBConnectionError(str(error))
        return supabase


