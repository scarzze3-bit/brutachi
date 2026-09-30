# app/settings.py
"""
Configuration and Resource Management
Supports paired ID-Email datasets, school lists, and response classifiers.
"""

import os
import csv

def read_lines_safe(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

def load_id_email_pairs(file_path):
    """
    Loads consistent ID to Email mappings from CSV, colon, or tab-delimited file.
    Expected formats:
      ID,Email
      ID:Email
      ID\tEmail
    """
    pairs = []
    if not os.path.exists(file_path):
        return pairs

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Try delimiter detection: comma, colon, tab, semicolon
            for delim in [",", ":", "\t", ";"]:
                if delim in line:
                    parts = line.split(delim, 1)
                    student_id = parts[0].strip()
                    email = parts[1].strip()
                    if student_id and email:
                        pairs.append((student_id, email))
                        break
    return pairs

def generate_pairs_from_pattern(ids, domain_or_pattern):
    """
    Generates consistent matching ID to Email pairs using a pattern or domain.
    E.g. pattern="{id}@student.apex.edu" or domain="student.apex.edu" -> "{id}@{domain}"
    """
    pairs = []
    for sid in ids:
        sid = sid.strip()
        if not sid:
            continue
        if "{id}" in domain_or_pattern:
            email = domain_or_pattern.replace("{id}", sid)
        else:
            email = f"{sid}@{domain_or_pattern.lstrip('@')}"
        pairs.append((sid, email))
    return pairs

# Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(BASE_DIR, "ressources")

# Resource paths
PAIRS_FILE = os.path.join(RES_DIR, "id_email_pairs.txt")
SCHOOLS_FILE = os.path.join(RES_DIR, "schools.txt")
IDS_FILE = os.path.join(RES_DIR, "ids.txt")
DOMAINS_FILE = os.path.join(RES_DIR, "domains.txt")
SUCCESS_MESSAGE_FILE = os.path.join(RES_DIR, "successMessage.txt")
INCORRECT_MESSAGE_FILE = os.path.join(RES_DIR, "incorrectMessage.txt")

# Default Global Data
DEFAULT_SCHOOLS = read_lines_safe(SCHOOLS_FILE)
DEFAULT_PAIRS = load_id_email_pairs(PAIRS_FILE)
DEFAULT_IDS = read_lines_safe(IDS_FILE)
DEFAULT_DOMAINS = read_lines_safe(DOMAINS_FILE)
SUCCESS_MESSAGES = read_lines_safe(SUCCESS_MESSAGE_FILE)
INCORRECT_MESSAGES = read_lines_safe(INCORRECT_MESSAGE_FILE)

# Network & Request Configuration
DEFAULT_TIMEOUT = 12
DEFAULT_DELAY = 0.5  # Seconds between trials
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
MAX_CONSECUTIVE_ERRORS = 5
