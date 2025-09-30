import os
import time
from math import ceil

from typing import Optional
import firebase_admin
from firebase_admin import credentials, db

from .config import ENV_VARS_CHECKED, check_environment_variables


def initialize_firebase() -> db:
    """
    Initializes Firebase Realtime Database connection using the credentials and URL from environment variables.
    Checks if the required environment variables are set before initialization.

    Returns:
        db: A reference to the Firebase Realtime Database.
    """
    if not ENV_VARS_CHECKED:
        check_environment_variables()

    cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS_PATH"))
    firebase_admin.initialize_app(cred, {"databaseURL": os.environ.get("FIREBASE_URL")})

    return db


def add_idea_to_firebase(
    user_id, user_name, title, description, timestamp=int(time.time())
) -> str:
    """
    Adds an idea to Firebase Realtime Database. Initializes Firebase if not already initialized.

    Args:
        user_id (str): The ID of the user submitting the idea.
        user_name (str): The name of the user submitting the idea.
        title (str): The title of the idea.
        description (str): The description of the idea.
        timestamp (int, optional): The timestamp of the idea submission. Defaults to the current time.

    Returns:
        str: The ID of the newly created idea entry in Firebase.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference("/ideas")

    # Create data object
    idea_data = {
        "user_id": user_id,
        "user_name": user_name,
        "title": title,
        "description": description,
        "timestamp": timestamp,
        "votes": {
            "upvotes": 0,
            "downvotes": 0,
        },
    }

    # Push data (creates a new entry with auto-generated ID)
    new_idea_ref = ref.push(idea_data)

    # Return the generated ID
    return new_idea_ref.key


def get_idea_from_firebase(idea_id) -> dict:
    """
    Retrieves an idea from Firebase by its ID. Initializes Firebase if not already initialized.

    Args:
        idea_id (str): The ID of the idea to retrieve.

    Returns:
        dict: A dictionary containing the idea's details, or None if the idea does not exist.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference(f"/ideas/{idea_id}")

    # Retrieve the idea data
    idea_data = ref.get()

    if idea_data is None:
        return None

    return {
        "id": idea_id,
        "user_id": idea_data["user_id"],
        "title": idea_data["title"],
        "description": idea_data["description"],
        "timestamp": idea_data.get("timestamp", None),
        "votes": idea_data.get("votes", {"upvotes": 0, "downvotes": 0}),
    }


def get_all_ideas_from_firebase() -> list:
    """
    Retrieves all ideas from Firebase. Initializes Firebase if not already initialized.

    Returns:
        list: A list of all ideas, each represented as a dictionary with keys
    """
    if not firebase_admin._apps:
        initialize_firebase()

    # Get a database reference
    ref = db.reference("/ideas")

    # Retrieve all ideas
    ideas_data = ref.get()

    if ideas_data is None:
        return []

    # Convert to list of dictionaries
    ideas_list = []
    for idea_id, idea in ideas_data.items():
        ideas_list.append(
            {
                "id": idea_id,
                "user_id": idea["user_id"],
                "title": idea["title"],
                "description": idea["description"],
                "timestamp": idea.get("timestamp", None),
                "votes": idea.get("votes", {"upvotes": 0, "downvotes": 0}),
            }
        )

    return ideas_list


def get_ideas_by_user_from_firebase(user_id) -> list:
    """
    Retrieves all ideas submitted by a specific user from Firebase.
    Initializes Firebase if not already initialized.

    Args:
        user_id (str): The user ID to filter ideas by.

    Returns:
        list: A list of ideas submitted by the specified user.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    return [
        idea for idea in get_all_ideas_from_firebase() if idea["user_id"] == user_id
    ]


def get_ideas_by_time_range_from_firebase(
    start_timetime, end_time=ceil(time.time())
) -> list:
    """
    Retrieves ideas submitted within a specific time range from Firebase.
    Initializes Firebase if not already initialized.

    Args:
        start_timetime (int): The start timestamp for filtering ideas.
        end_time (int, optional): The end timestamp for filtering ideas. Defaults to the current time.

    Returns:
        list: A list of ideas that fall within the specified time range.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    # Get all ideas
    ideas = get_all_ideas_from_firebase()
    # Filter ideas by timestamp
    filtered_ideas = [
        idea for idea in ideas if start_timetime <= idea.get("timestamp", 0) <= end_time
    ]
    return filtered_ideas


def get_idea_count_from_firebase(user_id=None) -> int:
    """
    Retrieves the count of ideas submitted by a user or all ideas if no user ID is provided.
    Initializes Firebase if not already initialized.

    Args:
        user_id (str, optional): The user ID to filter ideas by. If None, it counts all ideas.

    Returns:
        int: The count of ideas.
    """
    if not firebase_admin._apps:
        initialize_firebase()

    if user_id:
        ideas = get_ideas_by_user_from_firebase(user_id)
    else:
        ideas = get_all_ideas_from_firebase()
    return len(ideas)


def update_votes(
    idea_id: str,
    votes: Optional[tuple[int]] = None,
    votes_change: Optional[tuple[int]] = None,
) -> bool:
    """
    Updates the vote count for a specific idea in Firebase by the specified amount.
    Validates the input to ensure that either `votes` or `votes_change` is provided, but not both.
    Initializes Firebase if not already initialized.

    Args:
        idea_id (str): The ID of the idea to update votes for.
        votes (Optional[tuple[int]]): A tuple containing the new upvotes and downvotes.
            If provided, it will replace the current votes.
        votes_change (Optional[tuple[int]]): A dictionary containing the change in upvotes and downvotes.
            If provided, it will update the current votes by the specified amounts.
        If neither is provided, a ValueError will be raised.
        If both are provided, a ValueError will be raised.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    if votes is None and votes_change is None:
        raise ValueError("Either 'votes' or 'votes_change' must be provided.")
    elif votes is not None and votes_change is not None:
        raise ValueError("Only one of 'votes' or 'votes_change' can be provided.")

    if not firebase_admin._apps:
        initialize_firebase()

    idea_ref = db.reference(f"/ideas/{idea_id}")
    idea_data = idea_ref.get()

    if idea_data is None:
        return False

    if votes:
        upvotes, downvotes = votes
    elif votes_change:
        upvotes = idea_data["votes"].get("upvotes", 0) + votes_change[0]
        downvotes = idea_data["votes"].get("downvotes", 0) + votes_change[1]

    # Update the votes count by the specified amount
    new_votes = {
        "upvotes": upvotes,
        "downvotes": downvotes,
    }
    idea_ref.update({"votes": new_votes})
    return True
