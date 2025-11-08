"""
Google Classroom Service Module

This module provides helper functions to interact with the Google Classroom API
on behalf of authenticated teachers using their stored refresh tokens.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import current_app
import requests


def get_google_service(user):
    """
    Builds and returns a Google Classroom service object
    authenticated as the given user.
    
    Args:
        user: User model instance with a google_refresh_token
    
    Returns:
        Google Classroom service object, or None if the user has no token
        or if token refresh fails
    """
    refresh_token = user.google_refresh_token
    if not refresh_token:
        current_app.logger.warning(f"User {user.id} has no refresh token. Cannot build service.")
        return None

    try:
        # 1. Use the refresh token to get a new access token
        token_uri = "https://oauth2.googleapis.com/token"
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')

        response = requests.post(token_uri, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        })
        
        response_data = response.json()
        if 'access_token' not in response_data:
            current_app.logger.error(f"Failed to refresh token for user {user.id}: {response_data}")
            return None

        access_token = response_data['access_token']
        
        # 2. Build credentials with the new access token
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,  # Pass it along
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # 3. Build the Classroom service
        service = build('classroom', 'v1', credentials=creds)
        return service
        
    except Exception as e:
        current_app.logger.error(f"Failed to build Google service for user {user.id}: {e}")
        return None


def create_google_classroom(service, class_name, section=None, description=None):
    """
    Create a new Google Classroom course.
    
    Args:
        service: Authenticated Google Classroom service object
        class_name: Name of the class/course
        section: Optional section name
        description: Optional course description
    
    Returns:
        Dictionary with course information including 'id', or None if creation fails
    """
    try:
        course_body = {
            'name': class_name,
            'ownerId': 'me'  # 'me' = the authenticated teacher
        }
        
        if section:
            course_body['section'] = section
        if description:
            course_body['description'] = description
        
        course = service.courses().create(body=course_body).execute()
        current_app.logger.info(f"Successfully created Google Classroom: {course.get('id')}")
        return course
        
    except Exception as e:
        current_app.logger.error(f"Failed to create Google Classroom: {e}")
        return None


def get_classroom_info(service, classroom_id):
    """
    Get information about a Google Classroom course.
    
    Args:
        service: Authenticated Google Classroom service object
        classroom_id: Google Classroom course ID
    
    Returns:
        Dictionary with course information, or None if retrieval fails
    """
    try:
        course = service.courses().get(id=classroom_id).execute()
        return course
    except Exception as e:
        current_app.logger.error(f"Failed to get classroom info for {classroom_id}: {e}")
        return None


def add_student_to_classroom(service, classroom_id, student_email):
    """
    Add a student to a Google Classroom course.
    
    Args:
        service: Authenticated Google Classroom service object
        classroom_id: Google Classroom course ID
        student_email: Student's email address
    
    Returns:
        True if successful, False otherwise
    """
    try:
        invitation = {
            'courseId': classroom_id,
            'userId': student_email,
            'role': 'STUDENT'
        }
        service.courses().students().create(
            courseId=classroom_id,
            body={'userId': student_email}
        ).execute()
        current_app.logger.info(f"Successfully added student {student_email} to classroom {classroom_id}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to add student to classroom: {e}")
        return False


def list_user_classrooms(service):
    """
    List all Google Classroom courses for the authenticated user.
    
    Args:
        service: Authenticated Google Classroom service object
    
    Returns:
        List of course dictionaries, or empty list if retrieval fails
    """
    try:
        results = service.courses().list().execute()
        courses = results.get('courses', [])
        return courses
    except Exception as e:
        current_app.logger.error(f"Failed to list classrooms: {e}")
        return []

