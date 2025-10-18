"""
Test data factories for creating test objects.

This module provides factory functions for creating test data
with sensible defaults and easy customization.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid


def create_memo_data(
    memo_id: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    author: Optional[str] = None,
    tags: Optional[list] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a dictionary representing a memo with sensible defaults and optional overrides.
    
    Parameters:
        memo_id (Optional[str]): Identifier to use; a UUID string is generated if omitted.
        title (Optional[str]): Memo title; defaults to "Test Memo".
        content (Optional[str]): Memo content; defaults to "Test content".
        author (Optional[str]): Author identifier; defaults to "test-user".
        tags (Optional[list]): List of tags; defaults to ["test"].
        **kwargs: Additional fields to merge into the resulting memo dictionary.
    
    Returns:
        Dict[str, Any]: Memo data including `id`, `title`, `content`, `author`, `tags`,
        `created_at`, and `updated_at` (timestamps in UTC ISO 8601 format), plus any extra fields from `**kwargs`.
    """
    return {
        "id": memo_id or str(uuid.uuid4()),
        "title": title or "Test Memo",
        "content": content or "Test content",
        "author": author or "test-user",
        "tags": tags or ["test"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }


def create_user_data(
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Builds a user dictionary with sensible defaults and optional overrides.
    
    Parameters:
        user_id (Optional[str]): Unique identifier; generated if not provided.
        username (Optional[str]): Username; default is "testuser".
        email (Optional[str]): Email address; default is "test@example.com".
        role (Optional[str]): User role; default is "user".
        **kwargs: Additional fields to include in the resulting dictionary.
    
    Returns:
        Dict[str, Any]: User data with keys `id`, `username`, `email`, `role`, `created_at`, and any extra fields from `kwargs`.
    """
    return {
        "id": user_id or str(uuid.uuid4()),
        "username": username or "testuser",
        "email": email or "test@example.com",
        "role": role or "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }


def create_tag_data(
    tag_id: Optional[str] = None,
    name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a dictionary representing a tag for tests.
    
    Parameters:
        tag_id: Unique identifier to use; a UUID is generated if not provided.
        name: Tag name; defaults to "test-tag" when omitted.
        **kwargs: Additional fields merged into the returned dictionary.
    
    Returns:
        Dictionary with keys "id", "name", "created_at" (ISO 8601 UTC timestamp) and any extra fields from `kwargs`.
    """
    return {
        "id": tag_id or str(uuid.uuid4()),
        "name": name or "test-tag",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }


def create_batch_memos(count: int, **kwargs) -> list:
    """
    Generate a list of memo data dictionaries with sequential titles.
    
    Parameters:
        count (int): Number of memos to create.
        **kwargs: Common fields to merge into each memo.
    
    Returns:
        list: List of memo data dictionaries.
    """
    return [
        create_memo_data(
            title=f"Test Memo {i+1}",
            **kwargs
        )
        for i in range(count)
    ]


def create_batch_users(count: int, **kwargs) -> list:
    """
    Create multiple user data objects.
    
    Args:
        count: Number of users to create
        **kwargs: Common fields for all users
    
    Returns:
        List of user data dictionaries
    """
    return [
        create_user_data(
            username=f"testuser{i+1}",
            email=f"test{i+1}@example.com",
            **kwargs
        )
        for i in range(count)
    ]