"""
Repository classes for MongoDB operations in PDF RAG Chatbot application.
Provides CRUD operations for all document types with error handling.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.logger import get_logger
from models.database import (
    UserDocument, DocumentDocument, ChatSessionDocument,
    ChatMessageDocument, UserSettingsDocument
)

logger = get_logger(__name__)


# ==================== Base Repository ====================
class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str):
        self.database = database
        self.collection = database[collection_name]
        self.collection_name = collection_name

    async def create(self, document: Dict[str, Any]) -> str:
        """Create a new document"""
        try:
            result = await self.collection.insert_one(document)
            logger.info(f"Created document in {self.collection_name} with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create document in {self.collection_name}: {e}")
            raise Exception(f"Failed to create document: {e}")

    async def get_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(document_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None

    async def update(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """Update document by ID"""
        try:
            # Add updated timestamp if not present
            if 'updated_at' not in update_data:
                update_data['updated_at'] = datetime.utcnow()

            result = await self.collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated document {document_id} in {self.collection_name}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            return False

    async def delete(self, document_id: str) -> bool:
        """Delete document by ID"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(document_id)})
            if result.deleted_count > 0:
                logger.info(f"Deleted document {document_id} from {self.collection_name}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    async def list_all(self, filter_query: Dict[str, Any] = None,
                      skip: int = 0, limit: int = 100,
                      sort_field: str = "created_at", sort_direction: int = -1) -> List[Dict[str, Any]]:
        """List documents with optional filtering and pagination"""
        try:
            query = filter_query or {}
            cursor = self.collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
            documents = await cursor.to_list(length=limit)

            # Convert ObjectIds to strings
            for doc in documents:
                doc['_id'] = str(doc['_id'])

            return documents
        except Exception as e:
            logger.error(f"Failed to list documents from {self.collection_name}: {e}")
            return []

    async def count(self, filter_query: Dict[str, Any] = None) -> int:
        """Count documents matching filter"""
        try:
            query = filter_query or {}
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count documents in {self.collection_name}: {e}")
            return 0

    async def exists(self, document_id: str) -> bool:
        """Check if document exists"""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(document_id)}, {"_id": 1})
            return doc is not None
        except Exception as e:
            logger.error(f"Failed to check existence of document {document_id}: {e}")
            return False


# ==================== User Repository ====================
class UserRepository(BaseRepository):
    """Repository for user operations"""

    def __init__(self, database: AsyncIOMotorDatabase):
        super().__init__(database, "users")

    async def create_user(self, username: str, email: str, hashed_password: str,
                        role: str = "user") -> str:
        """Create a new user"""
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "role": role,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "preferences": {}
        }
        return await self.create(user_data)

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            doc = await self.collection.find_one({"username": username})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            doc = await self.collection.find_one({"email": email})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        return await self.update(user_id, {"last_login": datetime.utcnow()})

    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        return await self.update(user_id, {"preferences": preferences})

    async def activate_user(self, user_id: str) -> bool:
        """Activate user account"""
        return await self.update(user_id, {"is_active": True})

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        return await self.update(user_id, {"is_active": False})

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user password"""
        return await self.update(user_id, {"hashed_password": hashed_password})

    async def username_exists(self, username: str) -> bool:
        """Check if username exists"""
        try:
            count = await self.collection.count_documents({"username": username})
            return count > 0
        except Exception as e:
            logger.error(f"Failed to check username existence: {e}")
            return False

    async def email_exists(self, email: str) -> bool:
        """Check if email exists"""
        try:
            count = await self.collection.count_documents({"email": email})
            return count > 0
        except Exception as e:
            logger.error(f"Failed to check email existence: {e}")
            return False


# ==================== Document Repository ====================
class DocumentRepository(BaseRepository):
    """Repository for document operations"""

    def __init__(self, database: AsyncIOMotorDatabase):
        super().__init__(database, "documents")

    async def create_document(self, filename: str, original_filename: str, file_path: str,
                           file_size: int, user_id: str, category: str = "general") -> str:
        """Create a new document"""
        document_data = {
            "filename": filename,
            "original_filename": original_filename,
            "file_path": file_path,
            "file_size": file_size,
            "category": category,
            "user_id": user_id,
            "chunk_count": 0,
            "uploaded_at": datetime.utcnow(),
            "vector_index_path": None,
            "metadata": {},
            "is_deleted": False
        }
        return await self.create(document_data)

    async def get_user_documents(self, user_id: str, category: str = None,
                              skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get documents for a specific user"""
        query = {"user_id": user_id, "is_deleted": False}
        if category:
            query["category"] = category

        return await self.list_all(query, skip, limit, "uploaded_at", -1)

    async def search_documents(self, user_id: str, search_term: str,
                           skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Search documents by filename or category"""
        query = {
            "user_id": user_id,
            "is_deleted": False,
            "$or": [
                {"filename": {"$regex": search_term, "$options": "i"}},
                {"category": {"$regex": search_term, "$options": "i"}}
            ]
        }
        return await self.list_all(query, skip, limit, "uploaded_at", -1)

    async def soft_delete(self, document_id: str) -> bool:
        """Soft delete document (mark as deleted)"""
        return await self.update(document_id, {"is_deleted": True})

    async def permanent_delete(self, document_id: str) -> bool:
        """Permanently delete document"""
        # Also delete data from document_data collection
        try:
            await self.database.document_data.delete_one({"document_id": ObjectId(document_id)})
        except Exception as e:
            logger.warning(f"Failed to delete document data for {document_id}: {e}")
            
        return await self.delete(document_id)

    async def store_file_data(self, document_id: str, content: bytes) -> bool:
        """Store PDF file content in MongoDB"""
        try:
            await self.database.document_data.update_one(
                {"document_id": ObjectId(document_id)},
                {"$set": {"file_content": content}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store file data for {document_id}: {e}")
            return False

    async def get_file_data(self, document_id: str) -> Optional[bytes]:
        """Retrieve PDF file content from MongoDB"""
        try:
            data = await self.database.document_data.find_one({"document_id": ObjectId(document_id)})
            return data.get("file_content") if data else None
        except Exception as e:
            logger.error(f"Failed to retrieve file data for {document_id}: {e}")
            return None

    async def store_vector_index(self, document_id: str, index_data: bytes) -> bool:
        """Store serialized FAISS index in MongoDB"""
        try:
            await self.database.document_data.update_one(
                {"document_id": ObjectId(document_id)},
                {"$set": {"index_data": index_data}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store vector index for {document_id}: {e}")
            return False

    async def get_vector_index(self, document_id: str) -> Optional[bytes]:
        """Retrieve serialized FAISS index from MongoDB"""
        try:
            data = await self.database.document_data.find_one({"document_id": ObjectId(document_id)})
            return data.get("index_data") if data else None
        except Exception as e:
            logger.error(f"Failed to retrieve vector index for {document_id}: {e}")
            return None

    async def update_chunk_count(self, document_id: str, chunk_count: int) -> bool:
        """Update document chunk count"""
        return await self.update(document_id, {"chunk_count": chunk_count})

    async def update_vector_index(self, document_id: str, vector_index_path: str) -> bool:
        """Update document vector index path"""
        return await self.update(document_id, {"vector_index_path": vector_index_path})

    async def get_documents_by_ids(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple documents by IDs"""
        try:
            object_ids = [ObjectId(doc_id) for doc_id in document_ids]
            cursor = self.collection.find({"_id": {"$in": object_ids}, "is_deleted": False})
            documents = await cursor.to_list(length=len(document_ids))

            for doc in documents:
                doc['_id'] = str(doc['_id'])

            return documents
        except Exception as e:
            logger.error(f"Failed to get documents by IDs: {e}")
            return []


# ==================== Chat Repository ====================
class ChatRepository(BaseRepository):
    """Repository for chat operations"""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.session_collection = database["chat_sessions"]
        self.message_collection = database["chat_messages"]

    # ==================== Session Operations ====================
    async def create_session(self, user_id: str, title: str,
                          document_ids: List[str] = None) -> str:
        """Create a new chat session"""
        session_data = {
            "user_id": user_id,
            "title": title,
            "document_ids": document_ids or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "context_window": {}
        }
        result = await self.session_collection.insert_one(session_data)
        logger.info(f"Created chat session with ID: {result.inserted_id}")
        return str(result.inserted_id)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session by ID"""
        try:
            doc = await self.session_collection.find_one({"_id": ObjectId(session_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def get_user_sessions(self, user_id: str, is_active: bool = None,
                             skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Get chat sessions for a user"""
        try:
            query = {"user_id": user_id}
            if is_active is not None:
                query["is_active"] = is_active

            cursor = self.session_collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
            sessions = await cursor.to_list(length=limit)

            for session in sessions:
                session['_id'] = str(session['_id'])

            return sessions
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    async def update_session(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """Update chat session"""
        try:
            if 'updated_at' not in update_data:
                update_data['updated_at'] = datetime.utcnow()

            result = await self.session_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated chat session {session_id}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete chat session and associated messages"""
        try:
            # Delete session
            await self.session_collection.delete_one({"_id": ObjectId(session_id)})
            # Delete associated messages
            await self.message_collection.delete_many({"session_id": session_id})
            logger.info(f"Deleted chat session {session_id} and messages")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    # ==================== Message Operations ====================
    async def create_message(self, session_id: str, user_id: str, content: str,
                           is_user: bool, referenced_documents: List[str] = None,
                           citations: List[Dict[str, Any]] = None,
                           message_id: str = None) -> str:
        """Create a new chat message"""
        message_data = {
            "session_id": session_id,
            "user_id": user_id,
            "content": content,
            "is_user": is_user,
            "timestamp": datetime.utcnow(),
            "referenced_documents": referenced_documents or [],
            "citations": citations or [],
            "metadata": {"message_id": message_id} if message_id else {}
        }
        result = await self.message_collection.insert_one(message_data)
        logger.info(f"Created chat message with ID: {result.inserted_id}")

        # Update session's updated_at timestamp
        await self.update_session(session_id, {"updated_at": datetime.utcnow()})

        return str(result.inserted_id)

    async def get_session_messages(self, session_id: str, skip: int = 0,
                                 limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        try:
            cursor = self.message_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).skip(skip).limit(limit)

            messages = await cursor.to_list(length=limit)

            for message in messages:
                message['_id'] = str(message['_id'])

            return messages
        except Exception as e:
            logger.error(f"Failed to get session messages for {session_id}: {e}")
            return []

    async def get_recent_messages(self, session_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for context"""
        try:
            cursor = self.message_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", -1).limit(count)

            messages = await cursor.to_list(length=count)

            # Reverse to get chronological order
            messages = messages[::-1]

            for message in messages:
                message['_id'] = str(message['_id'])

            return messages
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []

    async def delete_message(self, message_id: str) -> bool:
        """Delete a specific message"""
        try:
            result = await self.message_collection.delete_one({"_id": ObjectId(message_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return False


# ==================== User Settings Repository ====================
class UserSettingsRepository(BaseRepository):
    """Repository for user settings operations"""

    def __init__(self, database: AsyncIOMotorDatabase):
        super().__init__(database, "user_settings")

    async def create_default_settings(self, user_id: str) -> str:
        """Create default settings for a user"""
        settings_data = {
            "user_id": user_id,
            "theme": "light",
            "language": "en",
            "notifications_enabled": True,
            "default_chunk_size": 500,
            "default_top_k": 5,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        return await self.create(settings_data)

    async def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get settings for a user"""
        try:
            doc = await self.collection.find_one({"user_id": user_id})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Failed to get settings for user {user_id}: {e}")
            return None

    async def update_settings(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            if 'updated_at' not in update_data:
                update_data['updated_at'] = datetime.utcnow()

            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated settings for user {user_id}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update settings for user {user_id}: {e}")
            return False
