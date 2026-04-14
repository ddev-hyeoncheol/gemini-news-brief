import functions_framework
import google.generativeai as genai

# from src.bigquery_client import save_to_bigquery


@functions_framework.http
def main(request):
    """
    Test Entry Point to verify GitHub-GCP synchronization.
    """

    # 1. Check if the code is synchronized
    message = "GitHub to GCP Sync Successful! v1.0"

    # 2. Print to Cloud Logs (You can see this in GCP Console)
    print(f"Log : {message}")

    # 3. Return response to browser
    return (message, 200)
