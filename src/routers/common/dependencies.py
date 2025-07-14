from typing import Annotated
from fastapi import Depends

from services.auth.http_bearer import jwt_token_bearer
from models import User


# By adding this dependency, we mark the endpoint as requiring a logged-in user.
LoggedUser = Annotated[User, Depends(jwt_token_bearer)]
