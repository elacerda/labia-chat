"""Testes unitários para o modelo ChatConversation."""

import uuid

from labia_chat.models.user import ChatConversation


class TestChatConversationModel:
    """Testes para o modelo ChatConversation."""

    def test_chat_conversation_has_correct_tablename(self):
        """Verifica que ChatConversation tem o nome da tabela correto."""
        assert ChatConversation.__tablename__ == "chat_conversations"

    def test_chat_conversation_in_base_metadata(self):
        """Verifica que ChatConversation está registrado no Base.metadata."""
        from labia_chat.db.base import Base

        assert "chat_conversations" in Base.metadata.tables
        assert Base.metadata.tables["chat_conversations"] is ChatConversation.__table__

    def test_chat_conversation_columns_exist(self):
        """Verifica que as colunas principais existem na metadata."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_conversations"]

        # Colunas obrigatórias
        assert "id" in table.columns
        assert "user_id" in table.columns
        assert "metadata" in table.columns
        assert "created_at" in table.columns
        assert "updated_at" in table.columns

        # Colunas opcionais
        assert "title" in table.columns
        assert "archived_at" in table.columns

    def test_chat_conversation_has_primary_key(self):
        """Verifica que id é a primary key."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_conversations"]
        assert table.primary_key is not None
        assert "id" in table.primary_key.columns

    def test_chat_conversation_has_foreign_key_to_chat_users(self):
        """Verifica que user_id tem foreign key para chat_users.id."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_conversations"]
        fks = [fk for fk in table.foreign_keys]
        assert any(fk.column.table.name == "chat_users" for fk in fks)

    def test_chat_conversation_has_metadata_column(self):
        """Verifica que metadata existe e mapeia para coluna 'metadata'."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_conversations"]
        assert "metadata" in table.columns

    def test_chat_conversation_has_conversation_metadata_attribute(self):
        """Verifica que ChatConversation tem atributo conversation_metadata."""
        assert hasattr(ChatConversation, "conversation_metadata")
        assert not hasattr(ChatConversation, "metadata_")

    def test_chat_conversation_metadata_maps_to_db_column(self):
        """Verifica que conversation_metadata mapeia para coluna 'metadata' no banco."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_conversations"]
        column = table.columns["metadata"]
        assert column is not None

    def test_chat_conversation_has_indexes(self):
        """Verifica que índices existem."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_conversations"]
        index_names = [idx.name for idx in table.indexes]

        assert "ix_chat_conversations_user_id" in index_names
        assert "ix_chat_conversations_created_at" in index_names
        assert "ix_chat_conversations_archived_at" in index_names

    def test_chat_conversation_repr(self):
        """Verifica que __repr__ funciona corretamente."""
        conv = ChatConversation(
            id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
            user_id=uuid.UUID("2ddf129b-efa5-4b81-896e-2ea26b383062"),
        )
        repr_str = repr(conv)
        assert "ChatConversation" in repr_str
