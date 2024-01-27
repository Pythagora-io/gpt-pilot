import os
MAX_GPT_MODEL_TOKENS = int(os.getenv('MAX_TOKENS', 8192))
MIN_TOKENS_FOR_GPT_RESPONSE = 600
MAX_QUESTIONS = 5
END_RESPONSE = "EVERYTHING_CLEAR"
API_CONNECT_TIMEOUT = 30  # timeout for connecting to the API and sending the request (seconds)
API_READ_TIMEOUT = 300  # timeout for receiving the response (seconds)
