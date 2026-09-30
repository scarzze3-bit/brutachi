# app/form_parser.py
"""
HTML Form Parser & Field Detection Module
Specifically tailored for Digital Learning Sign-Up / Registration pages.
Extracts input fields (school, student ID, email, csrf token, hidden inputs).
"""

from html.parser import HTMLParser
import urllib.parse
import re


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self._current_form = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = {k.lower(): (v or '') for k, v in attrs if k}
        tag_lower = tag.lower()

        if tag_lower == 'form':
            self._current_form = {
                'action': attrs_dict.get('action', ''),
                'method': attrs_dict.get('method', 'POST').upper(),
                'inputs': [],
                'selects': []
            }
        elif self._current_form is not None:
            if tag_lower == 'input':
                self._current_form['inputs'].append({
                    'name': attrs_dict.get('name', ''),
                    'type': attrs_dict.get('type', 'text').lower(),
                    'value': attrs_dict.get('value', ''),
                    'id': attrs_dict.get('id', ''),
                    'placeholder': attrs_dict.get('placeholder', '')
                })
            elif tag_lower == 'select':
                self._current_form['selects'].append({
                    'name': attrs_dict.get('name', ''),
                    'id': attrs_dict.get('id', '')
                })

    def handle_endtag(self, tag):
        if tag.lower() == 'form' and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None


def extract_form_details(html_content, base_url=""):
    """
    Parses HTML content, extracts the relevant sign-up form,
    and identifies candidate fields for school, ID, email, and CSRF token.
    """
    parser = FormParser()
    parser.feed(html_content)

    if not parser.forms:
        return None

    # Pick the best candidate form: prefer form containing email or student id or school
    chosen_form = parser.forms[0]
    for form in parser.forms:
        names = [inp['name'].lower() for inp in form['inputs']]
        combined = ' '.join(names)
        if any(key in combined for key in ['email', 'student', 'school', 'id']):
            chosen_form = form
            break

    action = chosen_form['action']
    if not action:
        action_url = base_url
    else:
        action_url = urllib.parse.urljoin(base_url, action)

    school_candidates = []
    id_candidates = []
    email_candidates = []
    csrf_candidates = []
    hidden_fields = {}

    for inp in chosen_form['inputs']:
        name = inp['name']
        input_type = inp['type']
        val = inp['value']
        combined = f"{name} {inp.get('id', '')} {inp.get('placeholder', '')}".lower()

        if input_type == 'submit' or not name:
            continue

        if input_type == 'hidden':
            hidden_fields[name] = val
            if any(term in combined for term in ['csrf', 'token', 'nonce', 'xsrf', '_token']):
                csrf_candidates.append(name)
            continue

        if input_type == 'email' or any(term in combined for term in ['email', 'mail']):
            email_candidates.append(name)
        elif any(term in combined for term in ['school', 'institution', 'college', 'campus', 'univ', 'academy', 'org']):
            school_candidates.append(name)
        elif any(term in combined for term in ['id', 'student', 'learner', 'matric', 'admission', 'reg', 'code']):
            id_candidates.append(name)

    # Check selects for school candidate
    for sel in chosen_form.get('selects', []):
        sel_name = sel.get('name', '')
        if sel_name and any(term in sel_name.lower() for term in ['school', 'institution', 'college', 'org']):
            if sel_name not in school_candidates:
                school_candidates.append(sel_name)

    return {
        'action_url': action_url,
        'method': chosen_form.get('method', 'POST'),
        'school_field': school_candidates[0] if school_candidates else None,
        'id_field': id_candidates[0] if id_candidates else None,
        'email_field': email_candidates[0] if email_candidates else None,
        'csrf_field': csrf_candidates[0] if csrf_candidates else (list(hidden_fields.keys())[0] if hidden_fields else None),
        'all_inputs': chosen_form['inputs'],
        'hidden_fields': hidden_fields
    }


def extract_csrf_token(html_content, csrf_field_name=None):
    """
    Extracts the latest CSRF token value from freshly reloaded HTML content.
    """
    if csrf_field_name:
        p1 = re.compile(rf'<input[^>]+name=["\']{re.escape(csrf_field_name)}["\'][^>]+value=["\']([^"\']*)["\']', re.IGNORECASE)
        m = p1.search(html_content)
        if m:
            return m.group(1)
        p2 = re.compile(rf'<input[^>]+value=["\']([^"\']*)["\'][^>]+name=["\']{re.escape(csrf_field_name)}["\']', re.IGNORECASE)
        m = p2.search(html_content)
        if m:
            return m.group(1)

    # Generic search for any hidden token/csrf input
    generic_pattern = re.compile(r'<input[^>]+name=["\']([^"\']*(?:csrf|token|_token|xsrf)[^"\']*)["\'][^>]+value=["\']([^"\']*)["\']', re.IGNORECASE)
    m = generic_pattern.search(html_content)
    if m:
        return m.group(2)

    return ""
