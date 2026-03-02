from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    EXEC = "exec"
    VIEW = "view"
