# exit.py
import os
import hashlib
import requests

from helpers.cli import terminate_running_processes
from utils.questionary import get_user_feedback


def send_telemetry(path_id):
    # Prepare the telemetry data
    telemetry_data = {
        "pathId": path_id,
        "event": "pilot-exit"
    }

    try:
        response = requests.post("https://api.pythagora.io/telemetry", json=telemetry_data)
        response.raise_for_status()
    except requests.RequestException as err:
        print(f"Failed to send telemetry data: {err}")


def send_feedback(feedback, path_id):
    """Send the collected feedback to the endpoint."""
    # Prepare the feedback data (you can adjust the structure as per your backend needs)
    feedback_data = {
        "pathId": path_id,
        "data": feedback,
        "event": "pilot-feedback"
    }

    try:
        response = requests.post("https://api.pythagora.io/telemetry", json=feedback_data)
        response.raise_for_status()
    except requests.RequestException as err:
        print(f"Failed to send feedback data: {err}")


def get_path_id():
    # Calculate the SHA-256 hash of the installation directory
    installation_directory = os.path.abspath(os.path.join(os.getcwd(), ".."))
    return hashlib.sha256(installation_directory.encode()).hexdigest()


def exit_gpt_pilot(ask_feedback=True):
    terminate_running_processes()
    path_id = get_path_id()
    send_telemetry(path_id)

    feedback = None
    if ask_feedback:
        feedback = get_user_feedback()
    if feedback:  # only send if user provided feedback
        send_feedback(feedback, path_id)
