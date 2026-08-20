"""script.cloud.gaming -- pure filtering logic, no xbmc* dependency so it
stays unit-testable with plain `python3 -m unittest`.
"""


def filter_services(services, chosen_csv):
    """Narrows `services` (a list of (name, url) tuples) down to whatever
    comma-separated names appear in `chosen_csv` (case-insensitive
    substring match, so e.g. "Boosteroid" matches "Google Stadia
    (Boosteroid)"). Falls back to every service unfiltered if
    `chosen_csv` is empty/blank or matches nothing, so behaviour is
    unchanged for anyone who never picked anything (plan 3aba4284's
    Cloud Gaming wizard step is what populates this, but skipping it
    entirely must not hide every service)."""
    chosen = [s.strip().lower() for s in (chosen_csv or '').split(',') if s.strip()]
    if not chosen:
        return services
    filtered = [s for s in services if any(c in s[0].lower() for c in chosen)]
    return filtered or services
