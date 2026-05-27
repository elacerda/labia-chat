"""Testes unitários para o modelo ChatMessage."""

import uuid

from labia_chat.models.user import ChatMessage


class TestChatMessageModel:
    """Testes para o modelo ChatMessage."""

    def test_chat_message_has_correct_tablename(self):
        """Verifica que ChatMessage tem o nome da tabela correto."""
        assert ChatMessage.__tablename__ == "chat_messages"

    def test_chat_message_in_base_metadata(self):
        """Verifica que ChatMessage está registrado no Base.metadata."""
        from labia_chat.db.base import Base

        assert "chat_messages" in Base.metadata.tables
        assert Base.metadata.tables["chat_messages"] is ChatMessage.__table__

    def test_chat_message_columns_exist(self):
        """Verifica que as colunas principais existem na metadata."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]

        # Colunas obrigatórias
        assert "id" in table.columns
        assert "conversation_id" in table.columns
        assert "role" in table.columns
        assert "content" in table.columns
        assert "sequence_index" in table.columns
        assert "metadata" in table.columns
        assert "created_at" in table.columns

        # Colunas opcionais
        assert "model" in table.columns

    def test_chat_message_has_primary_key(self):
        """Verifica que id é a primary key."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]
        assert table.primary_key is not None
        assert "id" in table.primary_key.columns

    def test_chat_message_has_foreign_key_to_chat_conversations(self):
        """Verifica que conversation_id tem foreign key para chat_conversations.id."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]
        fks = [fk for fk in table.foreign_keys]
        assert any(fk.column.table.name == "chat_conversations" for fk in fks)

    def test_chat_message_has_metadata_column(self):
        """Verifica que metadata existe e mapeia para coluna 'metadata'."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]
        assert "metadata" in table.columns

    def test_chat_message_has_message_metadata_attribute(self):
        """Verifica que ChatMessage tem atributo message_metadata."""
        assert hasattr(ChatMessage, "message_metadata")
        assert not hasattr(ChatMessage, "metadata_")

    def test_chat_message_metadata_maps_to_db_column(self):
        """Verifica que message_metadata mapeia para coluna 'metadata' no banco."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]
        column = table.columns["metadata"]
        assert column is not None

    def test_chat_message_has_indexes(self):
        """Verifica que índices existem."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]
        index_names = [idx.name for idx in table.indexes]

        assert "ix_chat_messages_conversation_id" in index_names
        assert "ix_chat_messages_created_at" in index_names

    def test_chat_message_has_unique_constraint(self):
        """Verifica que unique constraint (conversation_id, sequence_index) existe."""
        from labia_chat.db.base import Base

        table = Base.metadata.tables["chat_messages"]
        constraint_names = [c.name for c in table.constraints if c.name]

        assert "uq_chat_messages_conversation_sequence" in constraint_names

    def test_chat_message_repr(self):
        """Verifica que __repr__ funciona corretamente."""
        msg = ChatMessage(
            id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
            conversation_id=uuid.UUID("2ddf129b-efa5-4b81-896e-2ea26b383062"),
            role="user",
            content="Hello",
            sequence_index=0,
        )
        repr_str = repr(msg)
        assert "ChatMessage" in repr_str
