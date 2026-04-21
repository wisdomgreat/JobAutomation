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
        "from_patterns": ["@indeed.com", "@indeedmail.com", "noreply@indeed.com", "indeedapply@indeed.com"],
        "keywords": ["Indeed"],
        "name": "Indeed",
    },
    "linkedin": {
        "from_patterns": ["@linkedin.com", "jobs-noreply@linkedin.com"],
        "keywords": ["LinkedIn"],
        "name": "LinkedIn",
    },
    "glassdoor": {
        "from_patterns": ["@glassdoor.com"],
        "keywords": ["Glassdoor"],
        "name": "Glassdoor",
    },
    "ziprecruiter": {
        "from_patterns": ["@ziprecruiter.com"],
        "keywords": ["ZipRecruiter"],
        "name": "ZipRecruiter",
    },
    "monster": {
        "from_patterns": ["@monster.com", "@monster.ca", "@email.monster", "monster@email.monster.ca"],
        "keywords": ["Monster"],
        "name": "Monster",
    },
    "careerbuilder": {
        "from_patterns": ["@careerbuilder.com"],
        "keywords": ["CareerBuilder"],
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
        self.imap_server = config.IMAP_SERVER
        self.imap_port = config.IMAP_PORT
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        
    def connect(self) -> bool:
        """Connect to configured IMAP server with retry logic."""
        if self.connection:
            try:
                self.connection.noop()
                return True
            except:
                self.disconnect()

        try:
            print(f"[System] Connecting to Intelligence Core ({self.imap_server}:{self.imap_port})...")
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.connection.login(self.email_address, self.app_password)
            return True
        except Exception as e:
            print(f"[Error] Intelligence Core connection failed: {e}")
            self.connection = None
            return False

    def test_connection(self) -> bool:
        """Mission Readiness: Test IMAP connectivity."""
        if self.connect():
            try:
                self.connection.select("INBOX")
                print(f"[System] ✓ Intelligence Core Online ({self.imap_server}).")
                return True
            except Exception as e:
                print(f"[Error] Handshake failed: {e}")
                return False
        return False
        
        # Phase 32.3: Deep Cross-Reference Cache
        from src.resume_builder import parse_resume
        try:
            self.base_resume_text = parse_resume()
        except Exception:
            self.base_resume_text = ""

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
        job_title_lower = job_title.lower()
        
        # Phase 32.5: High-Precision Shortword Acronym Matching
        # Fuzzy matchers often fail on short strings like "IT"
        for role in config.TARGET_ROLES:
            role_lower = role.lower()
            
            # 1. Acronym Expansion (Phase 30.6)
            expanded_role = config.ACRONYM_MAP.get(role_lower)
            
            # 2. Exact Word Match (Highest Precision)
            if re.search(rf"\b{re.escape(role_lower)}\b", job_title_lower):
                best_score = max(best_score, 100)
                continue
            
            if expanded_role and re.search(rf"\b{re.escape(expanded_role.lower())}\b", job_title_lower):
                best_score = max(best_score, 100)
                continue
                
            # 3. Standard Fuzzy Match
            score = max(
                fuzz.ratio(job_title_lower, role_lower),
                fuzz.partial_ratio(job_title_lower, role_lower),
                fuzz.token_sort_ratio(job_title_lower, role_lower),
            )
            
            # Additional check against expanded role
            if expanded_role:
                ex_score = max(
                    fuzz.ratio(job_title_lower, expanded_role.lower()),
                    fuzz.partial_ratio(job_title_lower, expanded_role.lower())
                )
                score = max(score, ex_score)
            
            # 4. Boost for Acronyms (e.g., "IT" in "IT Specialist")
            if len(role) <= 3 and role_lower in job_title_lower.split():
                score = max(score, 95)
                
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
        except Exception as e:
            # Phase 3: Fail-Open Strategy (v30.3.5)
            # If AI is offline, fallback to keyword-based density score
            fallback_score = self._calculate_match_score(job_title)
            return fallback_score, f"Fallback Match (AI Offline: {str(e)[:40]}...)"

    def scan(self, days_back: int = 3, filter_roles: bool = True, allowed_platforms: Optional[list[str]] = None) -> list[JobAlert]:
        """
        Deep Discovery Engine (v30.7.0): Scan across multiple folders using keyword-first logic.
        """
        all_alerts = []
        if not self.connect():
            return []

        # Phase 30.7: Discovery Zones
        folders_to_scan = config.DISCOVERY_FOLDERS
        print(f"[System] Initiating Deep Hunt across {len(folders_to_scan)} mission zones...")

        since_date_imap = (datetime.now() - timedelta(days=int(config.DAYS_BACK))).strftime("%d-%b-%Y")

        for folder in folders_to_scan:
            try:
                print(f"[System] Entering Mission Zone: {folder}...")
                status, _ = self.connection.select(f'"{folder}"', readonly=True)
                if status != "OK":
                    print(f"  [Warning] Zone '{folder}' is restricted or missing. Skipping.")
                    continue

                for platform_key, info in JOB_ALERT_SENDERS.items():
                    # Support for platform filtering
                    if allowed_platforms and info["name"].lower() not in [p.lower() for p in allowed_platforms]:
                        continue

                    print(f"  [Discovery] Hunting for {info['name']} alerts...")
                    msg_ids = []
                    
                    # 1. Resilient Keyword Search (TEXT)
                    for kw in info.get("keywords", []):
                        try:
                            search_query = f'TEXT "{kw}"'
                            if not config.DEEP_SEARCH:
                                search_query = f'({search_query} SINCE {since_date_imap})'
                            
                            status, data = self.connection.search(None, search_query)
                            if status == "OK" and data[0]:
                                msg_ids.extend(data[0].split())
                        except Exception as e:
                            print(f"    [!] Search error for '{kw}': {e}")

                    # 2. Fallback Pattern Search (FROM)
                    if not msg_ids:
                        for pattern in info["from_patterns"]:
                            try:
                                search_query = f'FROM "{pattern}"'
                                if not config.DEEP_SEARCH:
                                    search_query = f'({search_query} SINCE {since_date_imap})'
                                
                                status, data = self.connection.search(None, search_query)
                                if status == "OK" and data[0]:
                                    msg_ids.extend(data[0].split())
                            except: continue

                    if not msg_ids:
                        continue

                    # Process unique IDs, newest first
                    msg_ids = sorted(list(set(msg_ids)), key=int, reverse=True)
                    msg_ids = msg_ids[:config.MAX_JOBS_PER_SCAN]
                    
                    print(f"    [Mission] Found {len(msg_ids)} packets. Extraction in progress...")
                    
                    for mid in msg_ids:
                        try:
                            status, data = self.connection.fetch(mid, "(RFC822)")
                            if status != "OK": continue
                            
                            msg = email.message_from_bytes(data[0][1])
                            alerts = self._parse_alert(msg, platform_key)
                            all_alerts.extend(alerts)
                        except Exception as e:
                            print(f"    [Error] Failed to extract packet {mid}: {e}")

            except Exception as e:
                print(f"[Error] Zone failure in {folder}: {e}")

        self.disconnect()
        
        if not all_alerts:
            print("[System] No new job intelligence discovered in this mission.")
            return []

        # Final ranking and filtering
        return self._rank_alerts(all_alerts)

    def _parse_alert(self, msg: email.message.Message, source_key: str) -> list[JobAlert]:
        """Process a single email message and extract jobs."""
        from_addr = self._decode_header_value(msg.get("From", ""))
        subject = self._decode_header_value(msg.get("Subject", ""))
        date_str = msg.get("Date", "")
        
        # Date filtering (v30.7: Precision filter after fetch)
        try:
            msg_dt = email.utils.parsedate_to_datetime(date_str)
            if msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            threshold_dt = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=config.DAYS_BACK)
            if not config.DEEP_SEARCH and msg_dt < threshold_dt:
                return []
        except Exception:
            pass

        html_body = self._extract_body_html(msg)
        text_body = self._extract_body_text(msg)
        
        soup = None
        if html_body:
            soup = BeautifulSoup(html_body, "lxml")
        elif text_body:
            soup = BeautifulSoup(text_body, "lxml")
        
        if not soup: return []

        if source_key == "indeed":
            jobs = self._parse_indeed_email(soup, text_body)
        elif source_key == "linkedin":
            jobs = self._parse_linkedin_email(soup, text_body)
        else:
            jobs = self._parse_generic_email(soup, text_body)

        parsed_alerts = []
        for job in jobs:
            fuzzy_score = self._calculate_match_score(job["title"])
            final_score = fuzzy_score
            match_reason = "Standard Match"
            
            # Telemetry
            print(f"  [Scan] Testing '{job['title'][:40]}' -> Score: {fuzzy_score}")
            
            if fuzzy_score >= config.MIN_ROLE_MATCH_SCORE:
                final_score, match_reason = self._llm_score_job(job["title"], job["description"])
                print(f"  [AI Scan] Intelligence review: {final_score} ({match_reason})")
            
            if final_score >= config.MATCH_SCORE_THRESHOLD:
                alert = JobAlert(
                    job_title=job["title"],
                    company=job.get("company", ""),
                    location=job.get("location", ""),
                    description=job["description"],
                    apply_url=job["url"],
                    source=JOB_ALERT_SENDERS[source_key]["name"],
                    email_date=date_str,
                    email_subject=subject,
                    match_score=final_score
                )
                parsed_alerts.append(alert)
        
        return parsed_alerts
        return parsed_alerts

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
