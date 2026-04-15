import sys
from pathlib import Path
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import config
from src.resume_builder import _text_to_pdf

def test_resume_gen():
    print("📝 Testing Hardened PDF Engine...")
    
    # Mock some realistic resume text that mirrors the user's profile
    with open("data/profile.yaml", "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    
    name = f"{profile['personal']['first_name']} {profile['personal']['last_name']}"
    contact = f"{profile['personal']['email']} | {profile['personal']['phone']} | {profile['personal']['address']} | {profile['personal']['linkedin_url']}"
    
    sample_text = f"""# {name}
{contact}

## Professional Summary
Dynamic IT professional with 15+ years of experience implementing and managing enterprise IT systems. 
Adept at streamlining cloud operations and enhancing security protocols.

## Skills
• Microsoft 365 Administration (Exchange, SharePoint, Azure AD)
• Cloud Infrastructure Management & Security
• Technical Strategy & Team Leadership

## Professional Experience
### Consultant IT | Managed Services | 2020 - Present
• Leading digital transformation projects for Fortune 500 clients.
• Implemented advanced identity management solutions reducing security breaches by 45%.
• Architected cloud-native infrastructure on Azure.

### Senior Systems Engineer | Global Networks | 2015 - 2020
• Managed 10,000+ endpoints using SCCM and Intune.
• Optimized network performance by 30% through strategic upgrades.
"""

    output_path = Path("test_resume.pdf")
    _text_to_pdf(sample_text, output_path)
    print(f"✅ Generated test resume at: {output_path.absolute()}")

if __name__ == "__main__":
    test_resume_gen()
