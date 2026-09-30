# app/main.py
"""
Entry Point for Digital Learning Sign-Up Automation Tool
Supports both Interactive Terminal Menu and Command-Line Flags.
"""

import sys
import argparse

from app.utils import (
    print_banner,
    automatic_mode,
    manual_mode,
    run_signup_trials,
    select_or_input_school
)
from app.settings import (
    DEFAULT_SCHOOLS,
    DEFAULT_PAIRS,
    DEFAULT_IDS,
    load_id_email_pairs,
    generate_pairs_from_pattern
)


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Digital Learning Platform Sign-Up Trial & Verification Tool"
    )
    parser.add_argument("--url", help="Target sign-up URL")
    parser.add_argument("--action-url", help="Form submission URL (if different from sign-up URL)")
    parser.add_argument("--school", help="School name or identifier")
    parser.add_argument("--school-field", default="school", help="Form input name for school")
    parser.add_argument("--id-field", default="student_id", help="Form input name for student ID")
    parser.add_argument("--email-field", default="email", help="Form input name for email")
    parser.add_argument("--csrf-field", default=None, help="Form input name for CSRF token")
    parser.add_argument("--pairs-file", help="Path to ID-Email pairs file (CSV or ID:Email)")
    parser.add_argument("--email-pattern", help="Generate emails from IDs using pattern, e.g. '{id}@student.apex.edu'")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between refreshed trials")
    parser.add_argument("--stop-on-match", action="store_true", help="Stop immediately when a match is found")
    parser.add_argument("--output", default="results.txt", help="File to store successful matches")
    parser.add_argument("--mode", choices=["auto", "manual"], help="Run in auto or manual mode via CLI")
    return parser.parse_args()


def interactive_menu():
    while True:
        print_banner()
        print("[+] Select an option:")
        print("  1-) Automatic Mode (Auto-detect fields from Sign-Up URL)")
        print("  2-) Manual Mode (Manually specify school, ID, email, csrf fields)")
        print("  3-) Run Quick Test with default pairs against a URL")
        print("  0-) Exit")

        try:
            choice = input("\n[+] Enter choice [0-3]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)

        if choice == "1":
            automatic_mode()
            break
        elif choice == "2":
            manual_mode()
            break
        elif choice == "3":
            url = input("[+] Enter Sign-Up URL to test: ").strip()
            if url:
                school = select_or_input_school()
                run_signup_trials(
                    url=url,
                    pairs=DEFAULT_PAIRS,
                    school=school,
                    school_field="school",
                    id_field="student_id",
                    email_field="email",
                    csrf_field="_csrf_token"
                )
            break
        elif choice == "0":
            print("Exiting.")
            sys.exit(0)
        else:
            print("[-] Invalid choice. Please try again.")


def main():
    args = parse_cli_args()

    # If --url is provided via CLI flags, run headlessly
    if args.url:
        print_banner()
        school = args.school or (DEFAULT_SCHOOLS[0] if DEFAULT_SCHOOLS else "Apex High School")

        # Resolve pairs
        if args.pairs_file:
            pairs = load_id_email_pairs(args.pairs_file)
        elif args.email_pattern:
            pairs = generate_pairs_from_pattern(DEFAULT_IDS, args.email_pattern)
        else:
            pairs = DEFAULT_PAIRS

        if not pairs:
            print("[-] Error: No matching ID-to-Email pairs available.")
            sys.exit(1)

        run_signup_trials(
            url=args.url,
            pairs=pairs,
            school=school,
            school_field=args.school_field,
            id_field=args.id_field,
            email_field=args.email_field,
            csrf_field=args.csrf_field,
            action_url=args.action_url,
            delay=args.delay,
            stop_on_first_match=args.stop_on_match,
            output_file=args.output
        )
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
