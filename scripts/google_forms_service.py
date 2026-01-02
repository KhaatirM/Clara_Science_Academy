"""
Google Forms Service Module

This module provides helper functions to interact with the Google Forms API
on behalf of authenticated teachers using their stored refresh tokens.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import current_app
import requests


def get_google_forms_service(user):
    """
    Builds and returns a Google Forms service object
    authenticated as the given user.
    
    Args:
        user: User model instance with a google_refresh_token
    
    Returns:
        Google Forms service object, or None if the user has no token
        or if token refresh fails
    """
    refresh_token = user.google_refresh_token
    if not refresh_token:
        current_app.logger.warning(f"User {user.id} has no refresh token. Cannot build Forms service.")
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
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # 3. Build the Forms service
        service = build('forms', 'v1', credentials=creds)
        return service
        
    except Exception as e:
        current_app.logger.error(f"Failed to build Google Forms service for user {user.id}: {e}")
        return None


def get_form_responses(service, form_id):
    """
    Get all responses for a Google Form.
    
    Args:
        service: Google Forms service object
        form_id: Google Form ID (not the full URL, just the ID)
    
    Returns:
        List of form responses, or None if error
    """
    try:
        # Get all responses
        responses = service.forms().responses().list(formId=form_id).execute()
        return responses.get('responses', [])
    except Exception as e:
        current_app.logger.error(f"Failed to get form responses for form {form_id}: {e}")
        return None


def get_form_info(service, form_id):
    """
    Get form information including questions.
    
    Args:
        service: Google Forms service object
        form_id: Google Form ID (not the full URL, just the ID)
    
    Returns:
        Form information dict, or None if error
    """
    try:
        form_info = service.forms().get(formId=form_id).execute()
        return form_info
    except Exception as e:
        current_app.logger.error(f"Failed to get form info for form {form_id}: {e}")
        return None


def create_google_form(service, title, description=None):
    """
    Create a new Google Form.
    
    Args:
        service: Google Forms service object
        title: Form title
        description: Optional form description
    
    Returns:
        Form dict with formId and responderUri, or None if error
    """
    try:
        form_body = {
            'info': {
                'title': title
            }
        }
        
        if description:
            form_body['info']['description'] = description
        
        form = service.forms().create(body=form_body).execute()
        current_app.logger.info(f"Successfully created Google Form: {form.get('formId')}")
        return form
    except Exception as e:
        current_app.logger.error(f"Failed to create Google Form: {e}")
        return None


def add_question_to_form(service, form_id, question_data):
    """
    Add a question to a Google Form.
    
    Args:
        service: Google Forms service object
        form_id: Google Form ID
        question_data: Dict with question structure:
            {
                'question': {
                    'required': bool,
                    'questionText': str,
                    'questionId': str (optional, auto-generated if not provided),
                    'choiceQuestion': {...} for multiple choice/true-false
                    or 'textQuestion': {...} for short answer/essay
                },
                'updateMask': str (e.g., 'question,question.required,question.choiceQuestion')
            }
    
    Returns:
        Updated form dict, or None if error
    """
    try:
        request_body = {
            'requests': [{
                'createItem': {
                    'item': question_data,
                    'location': {
                        'index': 0
                    }
                }
            }]
        }
        
        result = service.forms().batchUpdate(formId=form_id, body=request_body).execute()
        return result
    except Exception as e:
        current_app.logger.error(f"Failed to add question to form {form_id}: {e}")
        return None


def export_quiz_to_google_form(service, quiz_assignment, questions):
    """
    Export a native quiz to Google Forms format.
    
    Args:
        service: Google Forms service object
        quiz_assignment: Assignment model instance (quiz type)
        questions: List of QuizQuestion model instances with options
    
    Returns:
        Dict with 'form_id', 'form_url', or None if error
    """
    try:
        # Create the form with title and description
        form_body = {
            'info': {
                'title': quiz_assignment.title
            }
        }
        
        if quiz_assignment.description:
            form_body['info']['description'] = quiz_assignment.description
        
        form = service.forms().create(body=form_body).execute()
        form_id = form.get('formId')
        
        if not form_id:
            current_app.logger.error("Failed to get form ID from created form")
            return None
        
        requests = []
        
        # Add each question to the form
        for idx, question in enumerate(questions):
            item = {}
            question_item = {
                'question': {
                    'required': True
                }
            }
            
            if question.question_type == 'multiple_choice':
                # Get options for this question
                options = []
                for option in question.options:
                    options.append({'value': option.option_text})
                
                question_item['question']['choiceQuestion'] = {
                    'type': 'RADIO',
                    'options': options
                }
                
            elif question.question_type == 'true_false':
                # True/False as multiple choice with True/False options
                options = [{'value': 'True'}, {'value': 'False'}]
                
                question_item['question']['choiceQuestion'] = {
                    'type': 'RADIO',
                    'options': options
                }
                
            elif question.question_type == 'short_answer':
                question_item['question']['textQuestion'] = {
                    'paragraph': False
                }
                
            elif question.question_type == 'essay':
                question_item['question']['textQuestion'] = {
                    'paragraph': True
                }
            else:
                # Skip unsupported question types
                continue
            
            item['questionItem'] = question_item
            
            requests.append({
                'createItem': {
                    'item': item,
                    'location': {
                        'index': idx
                    }
                }
            })
        
        # Batch update the form with all questions
        if requests:
            batch_update_body = {'requests': requests}
            service.forms().batchUpdate(formId=form_id, body=batch_update_body).execute()
        
        # Get the form URL
        form_url = f"https://docs.google.com/forms/d/e/{form_id}/viewform"
        
        return {
            'form_id': form_id,
            'form_url': form_url
        }
        
    except Exception as e:
        current_app.logger.error(f"Failed to export quiz to Google Form: {e}")
        import traceback
        traceback.print_exc()
        return None

