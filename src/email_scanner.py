"""
Email Scanner Module
Connects to Yahoo Mail via IMAP to scan for job alert emails,
parses them, and returns structured JobAlert objects.
"""

import imaplib
import email
import email.message
import time
import email.utils
from email.header import decode_header
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup, Tag
from thefuzz import fuzz
import re
import config
from src.llm_provider import get_llm
from src.notifier import notify
from src.tracker import Tracker


@dataclass
class JobAlert:
    """Represents a parsed job alert from email."""
    job_title: str
    company: str
    location: str
    description: str
    apply_url: str
    source: str  # e.g., "Indeed", "LinkedIn", "Glassdoor"
    email_date: str
    email_subject: str
    match_score: int = 0  # Fuzzy match score against target roles


# Known job alert senders and their parsing patterns
JOB_ALERT_SENDERS = {
    "indeed": {
        "from_patterns": ["@indeed.com", "@indeedmail.com", "noreply@indeed.com"],
        "name": "Indeed",
    },
    "linkedin": {
        "from_patterns": ["@linkedin.com", "jobs-noreply@linkedin.com"],
        "name": "LinkedIn",
    },
    "glassdoor": {
        "from_patterns": ["@glassdoor.com"],
        "name": "Glassdoor",
    },
    "ziprecruiter": {
        "from_patterns": ["@ziprecruiter.com"],
        "name": "ZipRecruiter",
    },
    "monster": {
        "from_patterns": ["@monster.com"],
        "name": "Monster",
    },
    "careerbuilder": {
        "from_patterns": ["@careerbuilder.com"],
        "name": "CareerBuilder",
    },
}

# Words that indicate a link is NOT a real job title (noise filter)
NOISE_WORDS = {
    "view", "click", "here", "unsubscribe", "manage", "preferences",
    "settings", "privacy", "terms", "help", "contact", "learn more",
    "see all", "view all", "more jobs", "similar jobs", "update",
    "see all jobs", "see more", "see more jobs", "view more",
    "profile", "sign in", "log in", "logo", "indeed", "linkedin",
    "glassdoor", "©", "copyright", "all rights", "apply now",
    "easy apply", "see details", "view details", "job alert",
    "edit alert", "new jobs", "create alert", "recommended jobs",
    "top job picks for you", "edit", "save", "dismiss", "share",
    "job recommendations", "jobs for you", "your job alerts",
}


def _is_real_job_title(text: str) -> bool:
    """Check if text looks like a real job title vs. navigation junk."""
    text = text.strip()
    if not text or len(text) < 4:
        return False
    if len(text) > 120:
        return False
    text_lower = text.lower()
    # Reject if it's just a noise word/phrase
    if text_lower in NOISE_WORDS:
        return False
    # Reject if it starts with noise
    for nw in NOISE_WORDS:
        if text_lower == nw:
            return False
    # Reject if it's all caps short string (probably a button)
    if text.isupper() and len(text) < 15:
        return False
    # Reject URLs
    if text.startswith("http") or text.startswith("www"):
        return False
    # Should have at least one letter
    if not any(c.isalpha() for c in text):
        return False
    return True


def _clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove leading/trailing special chars
    text = text.strip('•·–—-|>')
    return text.strip()


def _extract_nearby_text(element: Tag, direction: str = "after", max_chars: int = 200) -> str:
    """Extract text near an element for context (company, location, desc)."""
    texts = []
    current = element
    for _ in range(5):  # Look at up to 5 siblings
        if direction == "after":
            current = current.find_next_sibling()
        else:
            current = current.find_previous_sibling()
        if not current:
            break
        t = current.get_text(strip=True)
        if t and len(t) > 2:
            texts.append(t)
    return " | ".join(texts)[:max_chars]


class EmailScanner:
    """Scans Yahoo Mail inbox for job alert emails."""

    def __init__(self):
        self.email_address = config.YAHOO_EMAIL
        self.app_password = config.YAHOO_APP_PASSWORD
        self.imap_server = "imap.mail.yahoo.com"
        self.imap_port = 993
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        
        # Phase 32.3: Deep Cross-Reference Cache
        from src.resume_builder import parse_resume
        try:
            self.base_resume_text = parse_resume()
        except Exception:
            self.base_resume_text = ""

    def connect(self) -> bool:
        """Connect to Yahoo Mail via IMAP SSL."""
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.connection.login(self.email_address, self.app_password)
            return True
        except imaplib.IMAP4.error as e:
            print(f"  [!] IMAP login failed: {e}")
            print("      Make sure you're using an App Password, not your regular password.")
            return False
        except Exception as e:
            print(f"  [!] Connection error: {e}")
            return False

    def disconnect(self):
        """Close the IMAP connection."""
        if self.connection:
            try:
                self.connection.logout()
            except Exception:
                pass
            self.connection = None

    def _identify_source(self, from_address: str) -> Optional[str]:
        """Identify which job platform sent the email."""
        from_lower = from_address.lower()
        for key, info in JOB_ALERT_SENDERS.items():
            for pattern in info["from_patterns"]:
                if pattern in from_lower:
                    return key
        return None

    def _decode_header_value(self, value: str) -> str:
        """Decode email header (handles encoded subjects)."""
        if not value:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)

    def _extract_body_html(self, msg: email.message.Message) -> str:
        """Extract HTML body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        else:
            if msg.get_content_type() == "text/html":
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    def _extract_body_text(self, msg: email.message.Message) -> str:
        """Extract plain text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        else:
            if msg.get_content_type() == "text/plain":
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    def _parse_indeed_email(self, soup: BeautifulSoup, text: str) -> list[dict]:
        """Parse Indeed job alert email for job listings."""
        jobs = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # Only consider Indeed job view links
            if "indeed.com" not in href:
                continue
            if not any(kw in href for kw in ["viewjob", "jk=", "clk", "/rc/", "pagead"]):
                continue

            # Deduplicate within same email
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # ── Extract job title ──
            # Strategy 1: The link text itself (most common in Indeed emails)
            link_text = _clean_text(link.get_text(strip=True))

            # Strategy 2: Look for a styled/bold element inside the link
            if not _is_real_job_title(link_text):
                bold = link.find(["b", "strong", "span"])
                if bold:
                    link_text = _clean_text(bold.get_text(strip=True))

            # Strategy 3: Check parent <td> or <div> for the job title
            if not _is_real_job_title(link_text):
                parent_td = link.find_parent(["td", "div"])
                if parent_td:
                    # Get the first meaningful text block in the parent
                    for child in parent_td.children:
                        if isinstance(child, Tag):
                            ct = _clean_text(child.get_text(strip=True))
                            if _is_real_job_title(ct):
                                link_text = ct
                                break
                        elif isinstance(child, str):
                            ct = _clean_text(child)
                            if _is_real_job_title(ct):
                                link_text = ct
                                break

            # Skip if we still don't have a valid job title
            if not _is_real_job_title(link_text):
                continue

            # ── Extract company & location from nearby elements ──
            company = ""
            location = ""
            description = ""

            parent = link.find_parent(["tr", "div", "td", "table"])
            if parent:
                # Get all text blocks in the parent container
                all_texts = []
                for elem in parent.find_all(["span", "td", "div", "p", "b", "strong"]):
                    t = _clean_text(elem.get_text(strip=True))
                    if t and t != link_text and len(t) > 2 and len(t) < 100:
                        all_texts.append(t)

                # First different text after title is usually company
                for t in all_texts:
                    if t != link_text and _is_real_job_title(t):
                        continue  # Might be another job title
                    if not company and t != link_text:
                        company = t
                    elif not location and t != company and t != link_text:
                        location = t
                        break

                # Get a description snippet from the full parent text
                full_text = _clean_text(parent.get_text(" ", strip=True))
                if len(full_text) > len(link_text) + 20:
                    description = full_text[:500]

            jobs.append({
                "title": link_text,
                "company": company,
                "location": location,
                "description": description,
                "url": href,
            })

        return jobs

    def _parse_linkedin_email(self, soup: BeautifulSoup, text: str) -> list[dict]:
        """Parse LinkedIn job alert email for job listings."""
        jobs = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            if "linkedin.com" not in href:
                continue
            if not any(kw in href for kw in ["jobs/view", "jobPosting", "/jobs/"]):
                continue

            if href in seen_urls:
                continue
            seen_urls.add(href)

            link_text = _clean_text(link.get_text(strip=True))

            if not _is_real_job_title(link_text):
                bold = link.find(["b", "strong", "span"])
                if bold:
                    link_text = _clean_text(bold.get_text(strip=True))

            if not _is_real_job_title(link_text):
                continue

            # Extract company/location from parent
            company = ""
            location = ""
            description = ""

            parent = link.find_parent(["tr", "div", "td", "table"])
            if parent:
                all_texts = []
                for elem in parent.find_all(["span", "td", "div", "p"]):
                    t = _clean_text(elem.get_text(strip=True))
                    if t and t != link_text and len(t) > 2 and len(t) < 100:
                        all_texts.append(t)

                for t in all_texts:
                    if not company and t != link_text:
                        company = t
                    elif not location and t != company and t != link_text:
                        location = t
                        break

                full_text = _clean_text(parent.get_text(" ", strip=True))
                if len(full_text) > len(link_text) + 20:
                    description = full_text[:500]

            jobs.append({
                "title": link_text,
                "company": company,
                "location": location,
                "description": description,
                "url": href,
            })

        return jobs

    def _parse_generic_email(self, soup: BeautifulSoup, text: str) -> list[dict]:
        """Generic parser for other job alert emails."""
        jobs = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            link_text = _clean_text(link.get_text(strip=True))

            if href in seen_urls:
                continue

            # Look for links that seem job-related
            if not any(kw in href.lower() for kw in ["job", "apply", "career", "position", "opening"]):
                continue

            if not _is_real_job_title(link_text):
                continue

            seen_urls.add(href)

            parent = link.find_parent(["tr", "div", "td"])
            context = _clean_text(parent.get_text(" ", strip=True)) if parent else ""

            jobs.append({
                "title": link_text,
                "company": "",
                "location": "",
                "description": context[:500],
                "url": href,
            })

        return jobs

    def _calculate_match_score(self, job_title: str) -> int:
        """Calculate fuzzy match score against target roles."""
        if not config.TARGET_ROLES:
            return 100  # No filter = everything matches

        best_score = 0
        for role in config.TARGET_ROLES:
            score = max(
                fuzz.ratio(job_title.lower(), role.lower()),
                fuzz.partial_ratio(job_title.lower(), role.lower()),
                fuzz.token_sort_ratio(job_title.lower(), role.lower()),
            )
            best_score = max(best_score, score)
        return best_score
    def _llm_score_job(self, job_title: str, description: str) -> tuple[int, str]:
        """
        Sovereign Intelligence: Uses AI to score a job match and provide reasoning.
        
        Output in this format:
        SCORE: [0-100]
        REASON: [Brief 1-sentence explanation]
        """
        prompt = f"Scoring match for {job_title}\nDescription: {description[:500]}"
        
        try:
            llm = get_llm()
            # Use a system prompt to enforce strict output
            result = llm.generate(prompt, system_prompt="You are a job matching assistant. Output SCORE then REASON.")
            
            score = 0
            reason = "Standard Match"
            
            score_match = re.search(r'SCORE:\s*(\d+)', result, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
            
            reason_match = re.search(r'REASON:\s*(.*)', result, re.IGNORECASE)
            if reason_match:
                reason = reason_match.group(1).strip()
                if len(reason) > 80: reason = reason[:77] + "..."
            
            return score, reason
        except Exception:
            pass
        return 0, "Error in match analysis"

    def scan(self, days_back: int = 3, filter_roles: bool = True, allowed_platforms: Optional[list[str]] = None) -> list[JobAlert]:
        """
        Scan inbox for job alert emails.

        Args:
            days_back: How many days back to search
            filter_roles: If True, only return jobs matching TARGET_ROLES / Resume
            allowed_platforms: Optional list of platform names to filter (e.g. ['linkedIn', 'indeed'])
        """
        alerts = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if not self.connection:
                    if not self.connect():
                        return []

                self.connection.select("INBOX")
                
                # Phase 23: Support fractional days for granular search
                days_float = float(days_back)
                threshold_dt = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days_float)
                
                # IMAP SINCE is only day-granular, so we get all from that day and filter locally
                since_date_imap = (datetime.now() - timedelta(days=int(days_float) + 1)).strftime("%d-%b-%Y")

                # Get all patterns
                all_patterns = []
                for info in JOB_ALERT_SENDERS.values():
                    all_patterns.extend(info["from_patterns"])

                for pattern in all_patterns:
                    try:
                        status, message_ids = self.connection.search(None, f'(FROM "{pattern}" SINCE {since_date_imap})')
                    except:
                        try:
                            status, message_ids = self.connection.search(None, f'(FROM "{pattern}")')
                        except: continue

                    if status != "OK" or not message_ids[0]:
                        continue

                    ids = message_ids[0].split()
                    recent_ids = ids[-config.MAX_JOBS_PER_SCAN:]
                    total_p = len(recent_ids)

                    for i, msg_id in enumerate(recent_ids, 1):
                        try:
                            print(f"[Intelligence] {source_key.upper()}: Processing mission alert {i} of {total_p}...")
                            status, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                            if status != "OK": continue

                            msg = email.message_from_bytes(msg_data[0][1])
                            from_addr = self._decode_header_value(msg.get("From", ""))
                            subject = self._decode_header_value(msg.get("Subject", ""))
                            date_str = msg.get("Date", "")
                            
                            # Phase 23: Precision filtering by timestamp
                            try:
                                msg_dt = email.utils.parsedate_to_datetime(date_str)
                                # Ensure timezone awareness for comparison
                                if msg_dt.tzinfo is None:
                                    msg_dt = msg_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                                
                                if msg_dt < threshold_dt:
                                    continue # Skip older than granular threshold
                            except Exception:
                                pass # Fallback to no filter if date is unparseable

                            source_key = self._identify_source(from_addr)
                            if not source_key: continue
                            
                            source_name = JOB_ALERT_SENDERS[source_key]["name"]
                            
                            # Phase 32.3: Platform Filtering
                            if allowed_platforms:
                                if source_name.lower() not in [p.lower() for p in allowed_platforms]:
                                    continue

                            html_body = self._extract_body_html(msg)
                            text_body = self._extract_body_text(msg)
                            
                            soup = None
                            if html_body:
                                soup = BeautifulSoup(html_body, "lxml")
                            elif text_body:
                                soup = BeautifulSoup(text_body, "lxml")
                            
                            if not soup: continue

                            # Parse based on source
                            if source_key == "indeed":
                                jobs = self._parse_indeed_email(soup, text_body)
                            elif source_key == "linkedin":
                                jobs = self._parse_linkedin_email(soup, text_body)
                            else:
                                jobs = self._parse_generic_email(soup, text_body)

                            for job in jobs:
                                fuzzy_score = self._calculate_match_score(job["title"])
                                final_score = fuzzy_score
                                match_reason = "Standard Match"
                                if fuzzy_score >= 50:
                                    # LLM-based Scoring (v32.9: Returns Score & Reason)
                                    final_score, match_reason = self._llm_score_job(job["title"], job["description"])
                                
                                # 4. Create Alert if it meets threshold
                                if final_score >= config.MATCH_SCORE_THRESHOLD:
                                    alert = JobAlert(
                                        job_title=job["title"],
                                        company=job.get("company", ""),
                                        location=job.get("location", ""),
                                        description=job.get("description", ""),
                                        apply_url=job.get("url", ""),
                                        source=source_name,
                                        email_date=date_str,
                                        email_subject=subject,
                                        match_score=final_score,
                                        match_reason=match_reason
                                    )
                                    alerts.append(alert)
                        except Exception:
                            continue

                # If we got here, success
                break

            except (imaplib.IMAP4.error, ConnectionError, TimeoutError) as e:
                print(f"  [!] IMAP/Socket error (Attempt {attempt+1}/{max_retries}): {e}")
                self.disconnect()
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    break
            except Exception as e:
                print(f"  [!] Unexpected error in scan: {e}")
                break

        # Deduplicate
        seen_urls = set()
        unique_alerts = []
        for alert in alerts:
            if alert.apply_url not in seen_urls:
                seen_urls.add(alert.apply_url)
                unique_alerts.append(alert)

        unique_alerts.sort(key=lambda a: a.match_score, reverse=True)
        return unique_alerts

    def check_for_outreach(self) -> int:
        """
        Scans for recruiter outreach and interview requests.
        Logs detections to Tracker and sends Desktop Notifications.
        Returns the number of NEW outreach messages detected.
        """
        print("🔍 Scanning for Recruiter Intelligence...")
        if not self.connection:
            if not self.connect(): return 0
            
        tracker = Tracker()
        new_count = 0
        
        # Sovereign Filter: Ignore common newsletter/travel noise
        SENDER_BLACKLIST = [
            "newsletter", "turkishairlines", "agoda", "nutrasystem", "asaptickets", 
            "travel", "deals@", "offers@", "premium@linkedin.com", "foundr.com"
        ]
        
        # Keywords that signal a human recruiter reaching out
        HIGH_SIGNAL_KEYWORDS = [
            "interview", "talk with", "phone screen", "availability", 
            "next steps", "met with", "meeting invitation", "schedule a time"
        ]
        
        try:
            self.connection.select("INBOX")
            # Scan last 100 emails regardless of source (Recruiters use personal/company email)
            status, message_ids = self.connection.search(None, "ALL")
            if status != "OK" or not message_ids[0]: return 0
            
            ids = message_ids[0].split()[-50:] # Focus on the absolute latest
            existing_outreach = [o['subject'] for o in tracker.get_outreach()]

            for msg_id in ids:
                status, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                if status != "OK": continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header_value(msg.get("Subject", ""))
                from_addr = self._decode_header_value(msg.get("From", ""))
                
                # Deduplication check
                if subject in existing_outreach: continue
                
                # Sovereign Filter check
                if any(blacklist in from_addr.lower() for blacklist in SENDER_BLACKLIST):
                    continue

                body = self._extract_body_text(msg) or self._extract_body_html(msg)
                body_lower = body.lower()
                
                # Score evidence of outreach
                # Require at least one HIGH SIGNAL or 'recruiter' + 'hiring' context
                is_outreach = any(kw in body_lower or kw in subject.lower() for kw in HIGH_SIGNAL_KEYWORDS)
                
                # Secondary check for 'recruiter' context
                if not is_outreach and ("recruiter" in body_lower or "hiring" in body_lower):
                     # Must also have a 'call' or 'chat' context to avoid generic job alerts
                     if any(kw in body_lower for kw in ["call", "chat", "speak", "interested in your background"]):
                         is_outreach = True

                if is_outreach:
                    print(f"  ✨ Recruiter Outreach Detected: {subject}")
                    
                    # Sentiment check (rudimentary)
                    sentiment = "positive" if "congratulations" in body_lower or "excited" in body_lower else "neutral"
                    
                    # Log to database
                    tracker.log_outreach(None, from_addr, subject, body[:1000], sentiment)
                    
                    # Send Mission Alert (Desktop Notification)
                    notify("MISSION ALERT: Recruiter Outreach", f"{from_addr}: {subject}")
                    new_count += 1

            return new_count
        except Exception as e:
            print(f"  [!] Outreach scan error: {e}")
            return 0


if __name__ == "__main__":
    config.validate()
    scanner = EmailScanner()
    print("Scanning Yahoo Mail for job alerts...")
    alerts = scanner.scan(days_back=7, filter_roles=False)
    print(f"\nFound {len(alerts)} job alerts:")
    for i, alert in enumerate(alerts, 1):
        print(f"\n  [{i}] {alert.job_title}")
        if alert.company:
            print(f"      Company: {alert.company}")
        print(f"      Source: {alert.source} | Score: {alert.match_score}%")
        print(f"      URL: {alert.apply_url[:80]}")
    scanner.disconnect()
