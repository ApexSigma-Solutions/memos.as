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
    Factory function for creating memo test data.
    
    Args:
        memo_id: Unique identifier (auto-generated if not provided)
        title: Memo title (default: "Test Memo")
        content: Memo content (default: "Test content")
        author: Author ID (default: "test-user")
        tags: List of tags (default: ["test"])
        **kwargs: Additional fields to include
    
    Returns:
        Dictionary with memo data
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
    Factory function for creating user test data.
    
    Args:
        user_id: Unique identifier (auto-generated if not provided)
        username: Username (default: "testuser")
        email: Email address (default: "test@example.com")
        role: User role (default: "user")
        **kwargs: Additional fields to include
    
    Returns:
        Dictionary with user data
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
    Factory function for creating tag test data.
    
    Args:
        tag_id: Unique identifier (auto-generated if not provided)
        name: Tag name (default: "test-tag")
        **kwargs: Additional fields to include
    
    Returns:
        Dictionary with tag data
    """
    return {
        "id": tag_id or str(uuid.uuid4()),
        "name": name or "test-tag",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }


def create_batch_memos(count: int, **kwargs) -> list:
    """
    Create multiple memo data objects.
    
    Args:
        count: Number of memos to create
        **kwargs: Common fields for all memos
    
    Returns:
        List of memo data dictionaries
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
