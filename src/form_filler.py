import time
import random
import re
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

from src.llm_provider import get_llm
from selenium.webdriver.common.action_chains import ActionChains

def _slow_type(element, text: str, delay_range: tuple = (0.05, 0.2)):
    """Type into an element with human-like variability in speed."""
    for char in str(text):
        element.send_keys(char)
        time.sleep(random.uniform(*delay_range))

def _stealth_click(element, driver):
    """Move to element and click with human-like behavior."""
    try:
        actions = ActionChains(driver)
        # Add randomized offset
        width = element.size['width']
        height = element.size['height']
        ox = random.randint(-int(width/4), int(width/4))
        oy = random.randint(-int(height/4), int(height/4))
        
        actions.move_to_element_with_offset(element, ox, oy)
        actions.perform()
        time.sleep(random.uniform(0.1, 0.3)) # Hesitation
        element.click()
    except Exception:
        # Fallback
        element.click()

# Mapping of field keywords to profile data keys
FIELD_MAP = {
    "first_name": ["first name", "first", "given name", "fname", "forename"],
    "middle_name": ["middle name", "middle", "mname"],
    "last_name": ["last name", "last", "surname", "family", "lname"],
    "preferred_name": ["preferred name", "nickname", "preferred"],
    "name": ["full name", "name", "your name", "candidate name"],
    "email": ["email", "e-mail", "email address", "contact email", "user_email"],
    "phone": ["phone", "mobile", "tel", "cell", "contact number", "phone number"],
    "phone_prefix": ["phone prefix", "country code", "area code"],
    "phone_type": ["phone type", "type of phone", "mobile or home"],
    "address": ["address", "street", "mailing address", "residential address", "home address"],
    "address_2": ["address line 2", "apt", "suite", "unit", "floor"],
    "city": ["city", "location", "town", "residence", "home city"],
    "province": ["state", "province", "region", "territory", "county"],
    "postal_code": ["postal", "zip", "zipcode", "postcode"],
    "country": ["country", "nationality", "citizenship"],
    "linkedin_url": ["linkedin", "profile url", "linkedin profile", "url"],
    "github_url": ["github", "github profile", "git"],
    "portfolio_url": ["portfolio", "website", "personal website", "blog"],
    "twitter_url": ["twitter", "x profile", "twitter profile"],
    "total_years": ["years of experience", "total years", "how many years", "work experience", "experience", "how long"],
    "current_title": ["current job title", "current role", "current title", "present title"],
    "summary": ["professional summary", "about you", "bio", "summary", "objective"],
    "authorized_to_work": ["authorized", "eligible", "right to work", "legally", "work in canada", "work in us", "work in "],
    "sponsorship_needed": ["sponsorship", "visa", "require sponsorship", "future sponsorship"],
    "work_permit_type": ["permit type", "work permit", "status"],
    "salary_expectation": ["salary expectation", "expected salary", "salary"],
    "salary_range": ["salary range", "range"],
    "notice_period": ["notice period", "notice", "availability"],
    "remote_preference": ["remote", "work style", "hybrid", "on-site"],
    "travel_percent": ["travel", "willing to travel", "travel percentage"],
    "password": ["password", "new password", "create password", "set password", "verify password"],
    "highest_degree": ["highest degree", "education level", "degree"],
    "technical_skills": ["technical skills", "skills", "technologies", "software"],
    "soft_skills": ["soft skills", "interpersonal", "attributes"],
    "primary_language": ["primary language", "native language", "mother tongue"],
    "other_languages": ["other languages", "alternative languages", "multilingual"],
    "security_clearance": ["clearance", "security", "background check"],
    "referred_by": ["referred", "how did you hear", "source", "find us", "advertisement"],
    "gender": ["gender", "sex", "how do you identify", "orientation"],
    "race": ["race", "ethnicity", "hispanic", "background"],
    "veteran": ["veteran", "military"],
    "disability": ["disability", "disabled", "physical or mental"],
}


def auto_fill_page(driver, profile_data, resume_path=None, cover_letter_path=None, resume_text=""):
    """
    Scans the current page for form fields and fills them using profile data.
    Returns the count of fields filled.
    """
    filled_count = 0
    
    # 1. Fill Text Inputs
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='tel'], input[type='password'], input[type='number']")
    for inp in inputs:
        if not inp.is_displayed() or inp.get_attribute("readonly"):
            continue
            
        try:
            label = _get_label(inp, driver).lower()
            matched_key = _match_field(label)

            # Phase 2: LLM-Assisted Classification
            if not matched_key and len(label) > 3:
                matched_key = _classify_field_with_llm(label)

            val = None
            if matched_key:
                # Check if already filled
                current_val = inp.get_attribute("value")
                if current_val and len(str(current_val).strip()) > 0:
                    continue

                val = profile_data.get(matched_key)
                # Fallback to resume extraction
                if not val and resume_text and matched_key in ["current_title", "total_years", "summary", "city"]:
                    val = _extract_info_from_resume(matched_key, resume_text)
            
            # Phase 12: LLM Fallback for unrecognized labels (The "Experience Years" Fix)
            if not val and len(label) > 5:
                # If it's a number field or the label suggests it, prompt the LLM
                is_num = (inp.get_attribute("type") == "number" or 
                          any(kw in label for kw in ["year", "how many", "decimal", "how long", "how much", "rate"]))
                val = _answer_question_with_llm(label, profile_data, resume_text, is_number=is_num)

            if val:
                print(f"    - Filling {label[:25]}... with {val}")
                inp.clear()
                _slow_type(inp, val)
                filled_count += 1
                time.sleep(random.uniform(0.5, 1.2)) # Pause between fields
        except Exception:
            continue
    
    # 2. Handle File Uploads
    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    for inp in file_inputs:
        try:
            label = _get_label(inp, driver).lower()
            aria_label = (inp.get_attribute("aria-label") or "").lower()
            is_resume = any(kw in label or kw in aria_label for kw in ["resume", "cv", "curriculum"])
            is_cover = any(kw in label or kw in aria_label for kw in ["cover letter", "letter of interest"])

            target_path = None
            if is_resume: target_path = resume_path
            elif is_cover: target_path = cover_letter_path

            if target_path and Path(target_path).exists():
                if not inp.is_displayed():
                    driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", inp)
                inp.send_keys(str(Path(target_path).absolute()))
                print(f"  📎 Uploaded: {Path(target_path).name}")
                filled_count += 1
        except Exception:
            continue

    # 3. Handle Select Dropdowns (Standard)
    select_elems = driver.find_elements(By.TAG_NAME, "select")
    for sel_elem in select_elems:
        try:
            if not sel_elem.is_displayed(): continue
            label = _get_label(sel_elem, driver).lower()
            select = Select(sel_elem)
            
            # Match directly
            matched_key = _match_field(label) or _classify_field_with_llm(label)
            val = profile_data.get(matched_key) if matched_key else None
            
            # AI Fallback
            if not val:
                val = _answer_question_with_llm(label, profile_data, resume_text, is_dropdown=True)

            if val:
                if _select_best_option(select, val):
                    filled_count += 1
        except Exception:
            continue

    # 3b. Handle Artdeco Dropdowns (LinkedIn Custom)
    artdeco_dropdowns = driver.find_elements(By.CSS_SELECTOR, "div.artdeco-dropdown, .fb-dropdown__select, .jobs-easy-apply-form-element")
    for drop in artdeco_dropdowns:
        try:
            if not drop.is_displayed(): continue
            label = _get_label(drop, driver).lower()
            if not label or len(label) < 3: continue

            # LinkedIn Specific: Skip if already has a value that isn't a placeholder
            try:
                current_text = drop.text.lower()
                if any(p in current_text for p in ["select", "choose", "option"]) is False and len(current_text) > 2:
                    continue
            except: pass

            # Consulting AI
            val = _answer_question_with_llm(label, profile_data, resume_text, is_dropdown=True)
            if val:
                # 1. Click to open
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", drop)
                _stealth_click(drop, driver)
                time.sleep(0.8) # Wait for animation
                
                # 2. Find options in the revealed menu
                options = driver.find_elements(By.CSS_SELECTOR, ".artdeco-dropdown__item, .fb-dropdown__option, [role='option'], .jobs-easy-apply-form-element__option")
                if not options:
                    options = driver.find_elements(By.XPATH, "//li[@role='option'] | //div[@role='option']")
                
                best_match = None
                for opt in options:
                    if val.lower() in opt.text.lower() or opt.text.lower() in val.lower():
                        best_match = opt
                        break
                
                if best_match:
                    _stealth_click(best_match, driver)
                    filled_count += 1
                    time.sleep(0.5)
        except Exception:
            continue

    # 4. Handle Textareas (Screening Questions)
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    for ta in textareas:
        try:
            if not ta.is_displayed() or (ta.get_attribute("value") and len(ta.get_attribute("value")) > 0):
                continue
            question = _get_label(ta, driver)
            answer = _answer_with_llm(question or "Professional background", resume_text)
            if answer:
                _slow_type(ta, answer)
                filled_count += 1
        except Exception:
            continue

    # 5. Handle Checkboxes (Agreements)
    checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
    for cb in checkboxes:
        try:
            if not cb.is_displayed() or cb.is_selected(): continue
            label = _get_label(cb, driver).lower()
            agreement_keywords = ["agree", "consent", "confirm", "understand", "terms", "policy", "truthful", "acknowledge"]
            if any(kw in label for kw in agreement_keywords):
                driver.execute_script("arguments[0].click();", cb)
                filled_count += 1
        except Exception:
            continue

    # 6. Handle Radio Buttons
    radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
    radio_groups = {}
    for rb in radios:
        try:
            name = rb.get_attribute("name")
            if name:
                if name not in radio_groups: radio_groups[name] = []
                radio_groups[name].append(rb)
        except: continue

    for name, buttons in radio_groups.items():
        try:
            if any(b.is_selected() for b in buttons): continue
            group_label = ""
            try:
                parent_fieldset = buttons[0].find_element(By.XPATH, "./ancestor::fieldset")
                group_label = parent_fieldset.find_element(By.TAG_NAME, "legend").text.lower()
            except:
                pass
            # Check for generic screening questions (previously employed, etc.)
            if not group_label:
                group_label = _get_label(buttons[0], driver).lower()
            
            # Heuristic for common questions
            if any(kw in group_label for kw in ["authorized", "eligible", "legal"]):
                _click_radio_by_text(driver, buttons, "yes")
                filled_count += 1
            elif any(kw in group_label for kw in ["sponsorship", "visa"]):
                _click_radio_by_text(driver, buttons, "no")
                filled_count += 1
            elif any(kw in group_label for kw in ["gender", "race", "ethnicity", "veteran", "disability"]):
                _click_radio_by_text(driver, buttons, "decline")
                filled_count += 1
            elif any(kw in group_label for kw in ["employed", "terminated", "crime", "convicted", "felony", "misdemeanor"]):
                # Usually best to answer NO to these "negative" screening questions
                _click_radio_by_text(driver, buttons, "no")
                filled_count += 1
            else:
                # Fallback to AI for unknown radio questions
                choice = _answer_question_with_llm(group_label, profile_data, resume_text, is_dropdown=True)
                if choice and _click_radio_by_text(driver, buttons, choice):
                    filled_count += 1
        except Exception:
            continue

    return filled_count

def _get_label(element, driver) -> str:
    """Tries various strategies to find the label text for an element."""
    # 0. Check for aria-label or placeholder directly first
    for attr in ["aria-label", "placeholder", "title", "name", "id"]:
        val = (element.get_attribute(attr) or "").lower()
        if val:
            # If we find a direct hit in FIELD_MAP with this attribute val, return it
            if _match_field(val): return val
            
    # 0.1 Check for aria-labelledby
    labelledby = element.get_attribute("aria-labelledby")
    if labelledby:
        try:
            label_elem = driver.find_element(By.ID, labelledby)
            if label_elem.text: return label_elem.text
        except NoSuchElementException:
            pass

    # 1. Look for <label for="element_id">
    id_attr = element.get_attribute("id")
    if id_attr:
        try:
            label_elem = driver.find_element(By.CSS_SELECTOR, f"label[for='{id_attr}']")
            if label_elem.text: return label_elem.text
        except NoSuchElementException:
            pass
            
    # 2. Look for aria-label
    aria = element.get_attribute("aria-label")
    if aria: return aria
    
    # 3. Look for parent label
    try:
        parent_label = element.find_element(By.XPATH, "./ancestor::label")
        if parent_label.text: return parent_label.text
    except NoSuchElementException:
        pass
    
    # 3b. LinkedIn Specific: Look for siblings with 'dash' or 'easy-apply' label classes
    try:
        parent_div = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'fb-dash-form-element') or contains(@class, 'jobs-easy-apply-form-element')]")
        label_text = parent_div.text.split('\n')[0]
        if label_text: return label_text
    except: pass
        
    # 4. Look for preceding/following text labels (complex nesting)
    try:
        # Search for any nearby text that might be a label
        siblings = driver.execute_script("""
            var elem = arguments[0];
            var labels = [];
            // Check immediate siblings first
            var parent = elem.parentElement;
            for (var child of parent.children) {
                if (child !== elem && (child.tagName === 'LABEL' || child.tagName === 'SPAN' || child.tagName === 'DIV' || child.tagName === 'H3' || child.tagName === 'P')) {
                    var txt = child.innerText.trim();
                    if (txt && txt.length < 150) labels.push(txt);
                }
            }
            // Check parent's siblings (common in some frameworks)
            var grand = parent.parentElement;
            if (grand && labels.length === 0) {
               for (var child of grand.children) {
                   if (child !== parent && (child.tagName === 'LABEL' || child.tagName === 'SPAN' || child.tagName === 'DIV' || child.tagName === 'P')) {
                       var txt = child.innerText.trim();
                       if (txt && txt.length < 150) labels.push(txt);
                   }
               }
            }
            return labels;
        """, element)
        if siblings: return siblings[0]
    except Exception:
        pass

    return element.get_attribute("name") or ""

def _click_radio_by_text(driver, buttons, target_text):
    """Clicks a radio button whose label contains the target text."""
    target_text = target_text.lower()
    for btn in buttons:
        try:
            label_text = _get_label(btn, driver).lower()
            if target_text in label_text:
                # Many modern sites hide radio buttons and style their <label> instead
                # Attempt to find the specific label and click it
                clicked = False
                btn_id = btn.get_attribute("id")
                if btn_id:
                    try:
                        lbl = driver.find_element(By.CSS_SELECTOR, f"label[for='{btn_id}']")
                        _stealth_click(lbl, driver)
                        clicked = True
                    except Exception:
                        pass
                
                # Try parent label if available
                if not clicked:
                    try:
                        parent = btn.find_element(By.XPATH, "./ancestor::label")
                        _stealth_click(parent, driver)
                        clicked = True
                    except Exception:
                        pass
                
                # Ultimate fallback to JS click on the button itself
                if not clicked:
                    driver.execute_script("arguments[0].click();", btn)
                
                return True
        except: continue
    return False

def _match_field(label: str) -> str:
    """Matches a label string to a profile data key."""
    for key, keywords in FIELD_MAP.items():
        if any(kw in label for kw in keywords):
            return key
    return None

def _slow_type(element, text: str):
    """Types text with human-like variability, pauses, and occasional typos/corrections."""
    try:
        element.clear()
        _short_sleep(0.1, 0.3)
        
        for i, char in enumerate(text):
            # Occasional "typo" and backspace (1% chance, not on first char)
            if i > 0 and random.random() < 0.01:
                typo_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                element.send_keys(typo_char)
                time.sleep(random.uniform(0.1, 0.25))
                element.send_keys("\uE003") # BACKSPACE
                time.sleep(random.uniform(0.1, 0.2))
            
            element.send_keys(char)
            
            # Non-linear typing speed
            # Longer pause on punctuation or spaces
            if char in ".,!?; ":
                time.sleep(random.uniform(0.15, 0.35))
            else:
                time.sleep(random.uniform(0.03, 0.12))
                
            # Occasional mid-word "thinking" pause
            if random.random() < 0.05:
                time.sleep(random.uniform(0.2, 0.6))
    except Exception:
        # Fallback to simple typing if element becomes stale
        try:
            element.send_keys(text)
        except: pass

def _short_sleep(min_s=0.1, max_s=1.0):
    time.sleep(random.uniform(min_s, max_s))


def _select_best_option(select, target_value: str):
    """Selects an option from a dropdown based on string similarity."""
    target = str(target_value).lower()
    # 1. Exact or substring match on visible text
    for option in select.options:
        opt_text = option.text.lower()
        if target in opt_text or opt_text in target:
            select.select_by_visible_text(option.text)
            return True
            
    # 2. Check for common sources if target is 'source' or 'referred_by'
    if any(kw in target for kw in ["source", "referral", "hear"]):
        sources = ["linkedin", "indeed", "glassdoor", "website", "other", "social", "job board"]
        for s in sources:
            for option in select.options:
                if s in option.text.lower():
                    select.select_by_visible_text(option.text)
                    return True

    # 3. Fallback to value if text didn't match
    try:
        select.select_by_value(target_value)
        return True
    except Exception:
        pass
    
    # 4. Final attempt: pick first non-empty option that isn't a prompt
    if not select.first_selected_option.get_attribute("value"):
        for option in select.options:
            if option.get_attribute("value") and len(option.get_attribute("value")) > 0:
                if "select" not in option.text.lower() and "choose" not in option.text.lower():
                    select.select_by_visible_text(option.text)
                    return True
    return False

def _extract_info_from_resume(field_name: str, resume_context: str) -> str:
    """Uses LLM to pull specific profile items from resume text."""
    try:
        llm = get_llm()
        prompt = f"""Extract the following information for a job application from the resume provided.
Target Field: {field_name}

Rules:
- Return ONLY the exact value, no sentences or intro.
- If it's plural (e.g. years of experience), return a number.
- If it's a current title, return just the title.
- If not found, return an empty string.

Resume Context:
{resume_context[:3000]}

Extracted Value:"""
        result = llm.generate(prompt, "You are a precise data extraction tool.").strip()
        # Clean up any quotes or surrounding text if LLM was chatty
        if result.startswith("'") or result.startswith('"'):
            result = result[1:-1]
        return result
    except Exception:
        return ""

def _answer_question_with_llm(question_label: str, profile_data: dict, resume_text: str, is_dropdown=False) -> str:
    """Uses LLM to generate a specific answer for an 'Additional Question' based on profile/resume."""
    try:
        current_title = profile_data.get("current_title", "Job Applicant")
        total_years = profile_data.get("total_years", "some")
        
        prompt = f"""You are answering a job application question for {profile_data.get('first_name', 'Wisdom Salami')}.
Resume Key Info:
- Current Title: {current_title}
- Total Exp: {total_years} years
- Top Skills: {profile_data.get('technical_skills', '')}

Question: {question_label}

Rules:
- Give a direct, professional answer. 
- If asking for a number (years), give just the number. 
- If asking for availability/dates, suggest 'Open to interview Monday-Friday during business hours'.
- If asking for yes/no, return 'Yes' or 'No'.
- If is_dropdown is True, return a single word that likely matches one of the options (e.g. 'Yes', 'No', 'Beginner', 'Expert').
- MAX 2 sentences.

Resume Snippet: {resume_text[:2000]}

Answer:"""
        llm = get_llm()
        result = llm.generate(prompt, "You are a precise job application assistant.").strip()
        # Minor cleanups
        result = result.replace('"', '').replace("'", "")
        return result
    except:
        return ""

def _answer_with_llm(question: str, resume_context: str) -> str:
    """Uses LLM to answer application questions based on resume and professional goals."""
    try:
        llm = get_llm()
        prompt = f"""You are a professional job seeker applying for a position. 
Answering the following application screening question concisely and professionally based on the candidate's resume.

Candidate Background Context:
{resume_context[:2500]}

Rules for your response:
1. If it is a Yes/No question, always answer 'Yes' (as we assume the candidate is qualified).
2. If it is about years of experience, provide a specific number derived from the resume.
3. If it is a behavioral question (e.g. "Why do you want to work here?"), provide a professional 2-3 sentence answer that highlights the candidate's strengths and interest.
4. Maintain a professional, confident, and polite tone.
5. Return ONLY the answer text, no preamble or quotes.

Question: {question}

Answer:"""
        return llm.generate(prompt, "You are a professional assistant filling out job applications.").strip()
    except Exception:
        return ""

def _classify_field_with_llm(label: str) -> str:
    """Uses LLM to classify an unknown form label into one of the FIELD_MAP keys."""
    try:
        llm = get_llm()
        # Get list of possible keys except 'password' for safety
        valid_keys = [k for k in FIELD_MAP.keys() if k != "password"]
        
        prompt = f"""Classify the following form field label into the most appropriate category from the list provided.
Target Label: "{label}"

Possible Categories:
{', '.join(valid_keys)}

Rules:
- If the label clearly matches one of the categories, return ONLY the category name.
- If it is a 'Yes/No' question about work authorization, use 'authorized_to_work'.
- If it is a 'Yes/No' question about visa sponsorship, use 'sponsorship_needed'.
- If no category is a good match, return 'none'.
- Do NOT provide explanations, just the category name or 'none'.

Classification:"""
        result = llm.generate(prompt, "You are a precise data classification tool.").strip().lower()
        if result in valid_keys:
            return result
    except Exception:
        pass
    return None
