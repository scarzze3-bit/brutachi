# Digital Learning Platform - Sign-Up Trial & Verification Tool

An automated, refreshed-session security verification and trial tool transformed specifically for **Digital Learning Platform Sign-Up Pages**.

## Key Features

- **Refreshes After Every Trial**: Each attempt initializes a fresh session and retrieves dynamic anti-CSRF / session tokens from the target URL before posting credentials.
- **Consistent Matching ID-to-Email**: Replaces blind Cartesian product attacks with aligned, consistent Student ID to Institutional Email pairs (via CSV, mapping files, or dynamic domain patterns).
- **Three-Input Support**: Specifically targets `School`, `Student ID`, and `Student Email`.
- **Intelligent Auto-Detection**: Automatically identifies input field names, forms, and hidden tokens from the target sign-up URL.
- **Rate-Limiting & Backoff Protection**: Automatically handles HTTP 429 Too Many Requests and CAPTCHA detection with randomized delay.
- **Detailed Audit Logging**: Outputs verified matches to `results.txt` and `results.json` with timestamps.
- **Built-in Mock Learning Server**: Includes a local mock portal (`target_example/mock_server.py`) for offline testing and verification.

---

## Installation

```bash
pip install -r requierements.txt
```
*(Only `requests` is required. The HTML parser uses standard library Python components).*

---

## Usage

### 1. Interactive Mode
Run the interactive wizard:
```bash
python3 -m app.main
```
Select **Option 1** for Automatic Form Detection, or **Option 2** for Manual Field Specification.

### 2. Command-Line (Headless) Mode
```bash
python3 -m app.main \
  --url "http://127.0.0.1:8080/signup" \
  --school "Apex High School" \
  --school-field "school" \
  --id-field "student_id" \
  --email-field "email" \
  --csrf-field "_csrf_token" \
  --pairs-file "ressources/id_email_pairs.txt" \
  --delay 0.5
```

### 3. Dynamic Pattern Generation
To automatically pair IDs with school email domains without manually creating a CSV:
```bash
python3 -m app.main \
  --url "http://127.0.0.1:8080/signup" \
  --school "Apex High School" \
  --email-pattern "{id}@student.apex.edu"
```

---

## Testing with the Local Mock Server

1. Start the mock digital learning portal:
```bash
python3 target_example/mock_server.py
```
*(Runs on `http://127.0.0.1:8080`)*

2. In another terminal, run the trial tool:
```bash
python3 -m app.main --url "http://127.0.0.1:8080" --stop-on-match
```

---

## Files in `ressources/`

- `id_email_pairs.txt`: Consistent matching student ID and email pairs (`ID,Email`).
- `schools.txt`: List of recognized school institutions.
- `ids.txt`: List of student ID numbers.
- `domains.txt`: School email domain suffixes.
- `successMessage.txt`: Substrings indicating successful sign-up or verification.
- `incorrectMessage.txt`: Substrings indicating mismatched or invalid records.
