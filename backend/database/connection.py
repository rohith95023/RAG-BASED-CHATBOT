"""
MongoDB connection management for PDF RAG Chatbot application.
Provides async database connection with Motor for MongoDB Atlas.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from config.settings import Settings
from utils.logger import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    """MongoDB Atlas connection manager with SRV support"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._is_connected = False

    async def connect(self, settings: Settings):
        """
        Establish connection to MongoDB Atlas and initialize database.
        Handles SRV connection strings and SSL/TLS properly.
        """
        try:
            # Parse SRV connection string and extract connection info
            connection_string = settings.MONGODB_URL

            # Create Motor client with Atlas-specific settings
            self.client = AsyncIOMotorClient(
                connection_string,
                maxPoolSize=50,
                minPoolSize=10,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                serverSelectionTimeoutMS=30000,
                retryWrites=True,  # Atlas requires this
                w="majority",  # Atlas requires this for better write performance
                uuidRepresentation="standard"
            )

            # Test connection
            await self.client.admin.command('ping')

            # Get database reference (create if doesn't exist)
            self.database = self.client[settings.MONGODB_DATABASE]

            # Initialize database and collections
            await self._initialize_database()

            self._is_connected = True
            logger.info(f"Successfully connected to MongoDB Atlas database: {settings.MONGODB_DATABASE}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Atlas: {e}")
            raise Exception(f"Database connection failed: {e}")

    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self._is_connected = False
            logger.info("Disconnected from MongoDB")

    async def _initialize_database(self):
        """
        Initialize database and create collections if they don't exist.
        """
        try:
            # List all existing collections
            existing_collections = await self.database.list_collection_names()

            # Define required collections
            required_collections = [
                'users',
                'documents',
                'chat_sessions',
                'chat_messages',
                'user_settings'
            ]

            # Create collections that don't exist
            for collection_name in required_collections:
                if collection_name not in existing_collections:
                    logger.info(f"Creating collection: {collection_name}")
                    await self.database.create_collection(collection_name)

            # Create indexes for performance
            await self._create_indexes()

            logger.info("Database initialization completed successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise Exception(f"Database initialization failed: {e}")

    async def _create_indexes(self):
        """
        Create database indexes for optimal query performance
        """
        try:
            # Users collection indexes
            await self.database.users.create_index([("username", 1)], unique=True)
            await self.database.users.create_index([("email", 1)], unique=True)
            await self.database.users.create_index([("created_at", -1)])

            # Documents collection indexes
            await self.database.documents.create_index([("user_id", 1)])
            await self.database.documents.create_index([("category", 1)])
            await self.database.documents.create_index([("uploaded_at", -1)])
            await self.database.documents.create_index([("is_deleted", 1)])

            # Chat sessions collection indexes
            await self.database.chat_sessions.create_index([("user_id", 1)])
            await self.database.chat_sessions.create_index([("updated_at", -1)])
            await self.database.chat_sessions.create_index([("is_active", 1)])

            # Chat messages collection indexes
            await self.database.chat_messages.create_index([("session_id", 1)])
            await self.database.chat_messages.create_index([("timestamp", -1)])
            await self.database.chat_messages.create_index([("user_id", 1)])

            # User settings collection indexes
            await self.database.user_settings.create_index([("user_id", 1)], unique=True)

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.warning(f"Failed to create some indexes: {e}")

    def get_database(self, settings: Settings) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if not self._is_connected:
            raise Exception("Database not connected")
        return self.database

    @asynccontextmanager
    async def get_database_session(settings: Settings):
        """
        Context manager for database session.
        Ensures connection is established and properly closed.
        """
        await db_manager.connect(settings)
        try:
            yield db_manager.get_database(settings)
        finally:
            # Keep connection open for reuse
            pass

    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._is_connected

    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            result = await self.database.command('ping')
            # Get database statistics
            stats = await self.database.command('collStats')
            total_collections = len(stats.get('collections', []))

            return {
                "status": "healthy",
                "ping": result.get('ok') == 1,
                "database": self.database.name,
                "collections": total_collections,
                "atlas_connection": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database": self.database.name if self.database else "unknown",
                "atlas_connection": False
            }


# Global database manager instance
db_manager = DatabaseManager()


@asynccontextmanager
async def get_database(settings: Settings):
    """
    Context manager for database session.
    Ensures connection is established and properly closed.
    """
    await db_manager.connect(settings)
    try:
        yield db_manager.get_database(settings)
    finally:
        # Keep connection open for reuse
        pass


async def get_db():
    """
    Dependency injection function for FastAPI routes.
    Returns database instance.
    """
    from config.settings import settings
    return db_manager.get_database(settings)