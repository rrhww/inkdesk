from __future__ import annotations

from pathlib import Path

import pytest

from inkdesk_server.vault_assets import SHARED_DIRS, SHARED_FILES, VAULT_TYPE_WIKI_DIRS


class TestVaultInitializeCreatesFullSharedStructure:
    """初始化创建设计文档规定的完整共享目录与默认文件。"""

    def test_creates_all_shared_dirs(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized()

        for dir_name in SHARED_DIRS:
            dir_path = temp_app_env / dir_name
            assert dir_path.is_dir(), f"缺少目录: {dir_name}"

    def test_creates_all_shared_files(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized()

        for asset in SHARED_FILES:
            file_path = temp_app_env / asset.relative_path
            assert file_path.is_file(), f"缺少文件: {asset.relative_path}"
            content = file_path.read_text(encoding="utf-8")
            assert len(content) > 50, f"文件内容过短: {asset.relative_path}"

    def test_every_initialized_asset_traces_to_design_doc(self):
        """保证 manifest 中的每一项都能在设计文档中找到依据。"""
        for asset in SHARED_FILES:
            assert asset.content.strip(), f"{asset.relative_path} 内容不应为空"
        for dir_name in SHARED_DIRS:
            assert dir_name


class TestVaultInitializeCodeProjectType:
    """代码项目型 Vault：wiki/ 下含 entities/ 和 concepts/ 子目录。"""

    def test_code_type_creates_entities_and_concepts_dirs(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized(vault_type="code")

        for wiki_dir in VAULT_TYPE_WIKI_DIRS["code"]:
            dir_path = temp_app_env / wiki_dir
            assert dir_path.is_dir(), f"代码项目型缺少目录: {wiki_dir}"

    def test_code_type_does_not_create_general_only_dirs(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized(vault_type="code")

        for wiki_dir in VAULT_TYPE_WIKI_DIRS["general"]:
            dir_path = temp_app_env / wiki_dir
            assert not dir_path.is_dir(), f"代码项目型不应创建: {wiki_dir}"


class TestVaultInitializeGeneralKnowledgeType:
    """通用知识型 Vault：wiki/ 下含 topics/、sources/ 和 queries/ 子目录。"""

    def test_general_type_creates_topics_sources_queries_dirs(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized(vault_type="general")

        for wiki_dir in VAULT_TYPE_WIKI_DIRS["general"]:
            dir_path = temp_app_env / wiki_dir
            assert dir_path.is_dir(), f"通用知识型缺少目录: {wiki_dir}"

    def test_general_type_does_not_create_code_only_dirs(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized(vault_type="general")

        for wiki_dir in VAULT_TYPE_WIKI_DIRS["code"]:
            dir_path = temp_app_env / wiki_dir
            assert not dir_path.is_dir(), f"通用知识型不应创建: {wiki_dir}"


class TestVaultRepeatedInitDoesNotOverwrite:
    """重复初始化不覆盖已有内容。"""

    def test_rerepeated_ensure_initialized_does_not_overwrite_agents_md(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized()

        agents_path = temp_app_env / "AGENTS.md"
        custom_content = "# Custom AGENTS\n\nUser content.\n"
        agents_path.write_text(custom_content, encoding="utf-8")

        service.ensure_initialized()

        assert agents_path.read_text(encoding="utf-8") == custom_content

    def test_repeated_ensure_initialized_preserves_user_wiki_page(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized()

        page_path = temp_app_env / "wiki" / "user-topic.md"
        custom_content = "---\ntype: concept\n---\n# User Topic\n\nUser written.\n"
        page_path.write_text(custom_content, encoding="utf-8")

        service.ensure_initialized()

        assert page_path.read_text(encoding="utf-8") == custom_content

    def test_ensure_initialized_is_idempotent(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized()

        snapshot = {}
        for root, _dirs, files in temp_app_env.walk():
            for f in files:
                abs_path = Path(root) / f
                rel = str(abs_path.relative_to(temp_app_env)).replace("\\", "/")
                snapshot[rel] = abs_path.read_text(encoding="utf-8")

        service.ensure_initialized()

        for rel, original_content in snapshot.items():
            current = (temp_app_env / rel).read_text(encoding="utf-8")
            assert current == original_content, f"文件被修改: {rel}"

    def test_repeated_init_preserves_existing_file_in_type_specific_dir(self, temp_app_env: Path):
        from inkdesk_server.core.config import get_settings
        from inkdesk_server.vault import VaultService

        service = VaultService(get_settings())
        service.ensure_initialized(vault_type="code")

        entities_dir = temp_app_env / "wiki" / "entities"
        page_path = entities_dir / "user-entity.md"
        custom_content = "---\ntype: entity\n---\n# My Entity\n\nUser maintained.\n"
        page_path.write_text(custom_content, encoding="utf-8")

        service.ensure_initialized(vault_type="code")

        assert page_path.read_text(encoding="utf-8") == custom_content
