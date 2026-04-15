import sys
from pathlib import Path
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import config
from src.applicant_profile import ApplicantProfile
from src.form_filler import _match_field, _classify_field_with_llm, FIELD_MAP
from src.resume_builder import generate_documents

def test_profile_loading():
    print("Testing Profile Loading...")
    profile = ApplicantProfile()
    data = profile.get_form_data()
    
    # Check new fields
    new_fields = ["phone_prefix", "address", "postal_code", "notice_period", "gender", "work_permit_type"]
    for field in new_fields:
        if field in data:
            print(f"  ✓ Found field: {field}")
        else:
            print(f"  ✗ Missing field: {field}")

def test_field_matching():
    print("\nTesting Field Matching Heuristics...")
    test_cases = {
        "What is your residential address?": "address",
        "ZIP Code": "postal_code",
        "Availability / Notice Period": "notice_period",
        "How do you identify?": "gender",
        "Sponsorship status": "sponsorship_needed"
    }
    
    for label, expected in test_cases.items():
        matched = _match_field(label.lower())
        if matched == expected:
            print(f"  ✓ Label '{label}' matched to {matched}")
        else:
            print(f"  ? Label '{label}' matched to {matched} (Expected: {expected})")

def test_resume_generation():
    print("\nTesting Resume/Cover Letter Generation Layout...")
    sample_job = {
        "title": "Senior AML Analyst",
        "company": "Finance Global",
        "location": "Toronto, ON",
        "description": "Expert in Anti-Money Laundering, identity management, and enterprise IT support."
    }
    
    try:
        paths = generate_documents(
            job_title=sample_job["title"],
            company=sample_job["company"],
            location=sample_job["location"],
            job_description=sample_job["description"]
        )
        print("  ✓ Documents generated successfully.")
        print(f"  Output directory: {paths['output_dir']}")
        return paths
    except Exception as e:
        print(f"  ✗ Generation failed: {e}")
        return None

if __name__ == "__main__":
    test_profile_loading()
    test_field_matching()
    paths = test_resume_generation()
    
    print("\nVerification Complete.")
    if paths:
        print(f"Check the output files in: {paths['output_dir']}")
