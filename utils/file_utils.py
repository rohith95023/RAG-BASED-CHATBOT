"""
File utilities for PDF chatbot.
Handles file operations including folder creation and file storage.
"""
import os
import shutil
from pathlib import Path
from typing import Optional


def ensure_directory_exists(directory_path: str) -> None:
    """
    Create directory if it doesn't exist.

    Args:
        directory_path: Path to the directory to create
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def save_uploaded_file(file_content: bytes, category: str, filename: str, base_path: str = "./data/documents") -> str:
    """
    Save uploaded file to category-specific folder.

    Args:
        file_content: Binary content of the file
        category: Category name for organizing files
        filename: Name of the file to save
        base_path: Base path for document storage

    Returns:
        Full path where file was saved
    """
    # Create category folder structure
    category_path = os.path.join(base_path, category)
    ensure_directory_exists(category_path)

    # Save file
    file_path = os.path.join(category_path, filename)
    with open(file_path, 'wb') as f:
        f.write(file_content)

    return file_path


def get_file_path(category: str, filename: str, base_path: str = "./data/documents") -> str:
    """
    Get full path for a file in a category.

    Args:
        category: Category name
        filename: File name
        base_path: Base path for document storage

    Returns:
        Full path to the file
    """
    return os.path.join(base_path, category, filename)


def file_exists(file_path: str) -> bool:
    """
    Check if a file exists.

    Args:
        file_path: Path to check

    Returns:
        True if file exists, False otherwise
    """
    return os.path.exists(file_path)


def delete_file(file_path: str) -> bool:
    """
    Delete a file if it exists.

    Args:
        file_path: Path to file to delete

    Returns:
        True if deleted, False if file didn't exist
    """
    if file_exists(file_path):
        os.remove(file_path)
        return True
    return False


def create_data_directories() -> None:
    """
    Create all necessary data directories for the application.
    """
    directories = [
        "./data/documents",
        "./data/vectors",
        "./data/logs"
    ]

    for directory in directories:
        ensure_directory_exists(directory)