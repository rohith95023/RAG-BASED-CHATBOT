"""
File utilities for PDF RAG Chatbot application.
Provides helper functions for file operations, uploads, and storage management.
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from utils.validators import sanitize_filename


def generate_unique_filename(original_filename: str, upload_dir: Path) -> str:
    """
    Generate a unique filename by appending a timestamp and hash if needed.
    """
    sanitized = sanitize_filename(original_filename)
    base_name, extension = Path(sanitized).stem, Path(sanitized).suffix

    # Create initial filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{base_name}_{timestamp}{extension}"

    # If file exists, append hash
    counter = 1
    while (upload_dir / unique_filename).exists():
        # Create hash of original filename + counter
        hash_obj = hashlib.md5(f"{sanitized}{counter}".encode())
        short_hash = hash_obj.hexdigest()[:8]
        unique_filename = f"{base_name}_{timestamp}_{short_hash}{extension}"
        counter += 1

    return unique_filename


def ensure_directory(directory: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    """
    return file_path.stat().st_size


def get_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """
    Calculate file hash for integrity checking.
    """
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def safe_delete_file(file_path: Path) -> bool:
    """
    Safely delete a file with error handling.
    """
    try:
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False


def safe_delete_directory(directory_path: Path) -> bool:
    """
    Safely delete a directory with error handling.
    """
    try:
        if directory_path.exists() and directory_path.is_dir():
            shutil.rmtree(directory_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting directory {directory_path}: {e}")
        return False


def move_file_with_structure(source: Path, destination: Path, create_dirs: bool = True) -> bool:
    """
    Move file, creating directory structure if needed.
    """
    try:
        if create_dirs:
            destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source), str(destination))
        return True
    except Exception as e:
        print(f"Error moving file from {source} to {destination}: {e}")
        return False


def copy_file_with_structure(source: Path, destination: Path, create_dirs: bool = True) -> bool:
    """
    Copy file, creating directory structure if needed.
    """
    try:
        if create_dirs:
            destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(source), str(destination))
        return True
    except Exception as e:
        print(f"Error copying file from {source} to {destination}: {e}")
        return False


def list_files_by_extension(directory: Path, extension: str = ".pdf") -> List[Path]:
    """
    List all files in directory with specified extension.
    """
    if not directory.exists():
        return []

    return list(directory.glob(f"*{extension}"))


def get_files_by_pattern(directory: Path, pattern: str) -> List[Path]:
    """
    Get files matching a glob pattern.
    """
    if not directory.exists():
        return []

    return list(directory.glob(pattern))


def clean_old_files(directory: Path, days_old: int = 30, extension: str = None) -> int:
    """
    Delete files older than specified days.
    Returns number of files deleted.
    """
    if not directory.exists():
        return 0

    deleted_count = 0
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)

    try:
        for file_path in directory.iterdir():
            if file_path.is_file():
                # Check extension filter
                if extension and not file_path.suffix.lower() == extension.lower():
                    continue

                # Check file age
                if file_path.stat().st_mtime < cutoff_time:
                    if safe_delete_file(file_path):
                        deleted_count += 1
    except Exception as e:
        print(f"Error cleaning old files in {directory}: {e}")

    return deleted_count


def get_directory_size(directory: Path) -> int:
    """
    Calculate total size of directory in bytes.
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.is_file():
                    total_size += file_path.stat().st_size
    except Exception as e:
        print(f"Error calculating directory size: {e}")

    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_file_mime_type(file_path: Path) -> Optional[str]:
    """
    Get MIME type of file based on extension.
    """
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.markdown': 'text/markdown',
        '.csv': 'text/csv',
        '.tsv': 'text/tab-separated-values',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.rtf': 'application/rtf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }

    return mime_types.get(file_path.suffix.lower())


def is_valid_pdf(file_path: Path) -> bool:
    """
    Check if file is a valid PDF by checking magic bytes.
    """
    if not file_path.exists() or not file_path.is_file():
        return False

    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    except Exception:
        return False


def create_temp_file(content: bytes, suffix: str = ".tmp") -> Path:
    """
    Create a temporary file with the given content.
    Returns the path to the created file.
    """
    import tempfile

    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'wb') as temp_file:
            temp_file.write(content)
        return Path(temp_path)
    except Exception as e:
        os.close(fd)
        raise Exception(f"Failed to create temp file: {e}")


def read_file_chunks(file_path: Path, chunk_size: int = 8192) -> bytes:
    """
    Generator to read file in chunks.
    """
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            yield chunk


def get_file_creation_date(file_path: Path) -> datetime:
    """
    Get file creation date.
    """
    return datetime.fromtimestamp(file_path.stat().st_ctime)


def get_file_modification_date(file_path: Path) -> datetime:
    """
    Get file modification date.
    """
    return datetime.fromtimestamp(file_path.stat().st_mtime)


def ensure_unique_path(base_path: Path) -> Path:
    """
    Ensure a unique path by appending numbers if the path exists.
    """
    if not base_path.exists():
        return base_path

    counter = 1
    while True:
        new_path = base_path.with_name(f"{base_path.stem}_{counter}{base_path.suffix}")
        if not new_path.exists():
            return new_path
        counter += 1


def create_backup_file(original_path: Path, backup_dir: Path = None) -> Path:
    """
    Create a backup of a file.
    """
    if backup_dir is None:
        backup_dir = original_path.parent / "backups"

    ensure_directory(backup_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"{original_path.stem}_{timestamp}_backup{original_path.suffix}"
    backup_path = backup_dir / backup_filename

    if copy_file_with_structure(original_path, backup_path):
        return backup_path
    raise Exception(f"Failed to create backup for {original_path}")


def cleanup_empty_directories(directory: Path) -> int:
    """
    Remove empty directories recursively.
    Returns number of directories removed.
    """
    removed_count = 0
    try:
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                if not list(dir_path.iterdir()):  # Directory is empty
                    if safe_delete_directory(dir_path):
                        removed_count += 1
    except Exception as e:
        print(f"Error cleaning empty directories: {e}")

    return removed_count
