from __future__ import annotations

from hashlib import sha256
from uuid import UUID, uuid5


DEFAULT_ORGANIZATION_ID = "organization-default"
DEFAULT_ORGANIZATION_SLUG = "default"
DEFAULT_ORGANIZATION_NAME = "Default Organization"
DEFAULT_SPACE_NAMESPACE = UUID("b1d4a53b-5bc0-4887-9422-0bd732d45cb0")
ACTIVE_STATUS = "active"
ORGANIZATION_SCOPE = "organization"
PROJECT_SCOPE = "project"
PERSONAL_SCOPE = "personal"


def deterministic_id(identity: str) -> str:
    return str(uuid5(DEFAULT_SPACE_NAMESPACE, identity))


def membership_id(user_id: str) -> str:
    return deterministic_id(f"membership:{DEFAULT_ORGANIZATION_ID}:{user_id}")


def project_space_id(workspace_id: str) -> str:
    return deterministic_id(f"project:{DEFAULT_ORGANIZATION_ID}:{workspace_id}")


def personal_space_id(workspace_id: str, user_id: str) -> str:
    return deterministic_id(f"personal:{DEFAULT_ORGANIZATION_ID}:{workspace_id}:{user_id}")


def organization_space_id() -> str:
    return deterministic_id(f"organization:{DEFAULT_ORGANIZATION_ID}")


def personal_slug(workspace_slug: str, user_id: str) -> str:
    return f"personal-{workspace_slug}-{sha256(user_id.encode('utf-8')).hexdigest()[:12]}"
