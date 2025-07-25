# gemini_utils.py
# This module configures the Gemini API for use in the application.
import os
import google.generativeai as genai
from dotenv import load_dotenv


def configure_gemini():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")
