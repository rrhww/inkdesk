from __future__ import annotations


def load_orm_models() -> None:
    from inkdesk_server import models  # noqa: F401
    from inkdesk_server.modules.spaces import models as space_models  # noqa: F401
