import reflex as rx
import logging
from typing import ClassVar

from dashboard.state.roles import UserRole

logger = logging.getLogger("dashboard.auth")
logging.basicConfig(level=logging.INFO)

class AuthState(rx.State):
    """Very simple demo authentication state with roles."""

    # Demo users: username -> (password, role)
    DEMO_USERS: ClassVar[dict[str, tuple[str, UserRole]]] = {
        "admin": ("admin", UserRole.ADMIN),
        "exec": ("exec", UserRole.EXEC),
        "viewer": ("view", UserRole.VIEW),
    }

    # session
    is_authenticated: bool = False
    username: str = ""
    role: UserRole = UserRole.VIEW

    # form fields
    login_user: str = ""
    login_password: str = ""

    # error
    error: str = ""

    # --- role helpers ---
    @rx.var
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @rx.var
    def can_execute(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.EXEC)

    # --- actions ---
    @rx.event
    def set_user(self, v: str):
        self.login_user = v

    @rx.event
    def set_password(self, v: str):
        self.login_password = v

    @rx.event
    def login(self):

        logger.info("Attempting login for user: %s", self.login_user)
        
        entry = self.DEMO_USERS.get(self.login_user)
        if entry and entry[0] == self.login_password:
            self.is_authenticated = True
            self.username = self.login_user
            self.role = entry[1]
            self.error = ""
            self.login_password = ""
            return rx.redirect("/")
        else:
            self.error = "Invalid credentials"

    @rx.event
    def logout(self):
        self.is_authenticated = False
        self.username = ""
        self.role = UserRole.VIEW
        self.login_user = ""
        self.login_password = ""
        self.error = ""
        return rx.redirect("/login")

    @rx.event
    def require_login(self):
        if not self.is_authenticated:
            return rx.redirect("/login")
