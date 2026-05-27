"""Testes unitários para o modelo ChatUser."""

import uuid

from labia_chat.models.user import ChatUser


class TestChatUserModel:
    """Testes para o modelo ChatUser."""

    def test_chat_user_has_correct_tablename(self):
        """Verifica que ChatUser tem o nome da tabela correto."""
        assert ChatUser.__tablename__ == "chat_users"

    def test_chat_user_in_base_metadata(self):
        """Verifica que ChatUser está registrado no Base.metadata."""
        from labia_chat.db.base import Base

        assert "chat_users" in Base.metadata.tables
        assert Base.metadata.tables["chat_users"] is ChatUser.__table__

    def test_chat_user_columns_exist(self):
        """Verifica que as colunas principais existem na metadata."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_users"]

        # Colunas obrigatórias
        assert "id" in table.columns
        assert "adss_id" in table.columns
        assert "username" in table.columns
        assert "is_active" in table.columns

        # Colunas opcionais
        assert "email" in table.columns
        assert "full_name" in table.columns
        assert "is_staff" in table.columns
        assert "is_superuser" in table.columns
        assert "roles" in table.columns
        assert "created_at" in table.columns
        assert "updated_at" in table.columns
        assert "last_seen_at" in table.columns

    def test_chat_user_has_primary_key(self):
        """Verifica que id é a primary key."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_users"]
        assert table.primary_key is not None
        assert "id" in table.primary_key.columns

    def test_chat_user_has_unique_constraint_on_adss_id(self):
        """Verifica que adss_id tem constraint unique."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_users"]
        # Verifica que existe um unique constraint em adss_id
        # O SQLAlchemy usa _sorted_constraints para armazenar as constraints
        constraint_names = [c.name for c in table.constraints if c.name is not None]
        assert "uq_chat_users_adss_id" in constraint_names

    def test_chat_user_has_indexes(self):
        """Verifica que índices existem para username e email."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_users"]
        index_names = [idx.name for idx in table.indexes]

        assert "ix_chat_users_username" in index_names
        assert "ix_chat_users_email" in index_names

    def test_chat_user_repr(self):
        """Verifica que __repr__ funciona corretamente."""
        user = ChatUser(
            id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
            adss_id=uuid.UUID("2ddf129b-efa5-4b81-896e-2ea26b383062"),
            username="testuser",
        )
        repr_str = repr(user)
        assert "ChatUser" in repr_str
        assert "testuser" in repr_str
