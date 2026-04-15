import sys
from pathlib import Path
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import config
from src.resume_builder import _markdown_to_docx

def test_docx_gen():
    print("📝 Testing Hardened DOCX Engine...")
    
    # Mock realistic content
    with open("data/profile.yaml", "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    
    name = f"{profile['personal']['first_name']} {profile['personal']['last_name']}"
    contact = f"{profile['personal']['email']} | {profile['personal']['phone']} | {profile['personal']['address']} | {profile['personal']['linkedin_url']}"
    
    # Include a blank line between name and contact to test robustness
    sample_text = f"""# {name}

{contact}

## Professional Summary
This is a professional summary that should stay perfectly aligned.

## Professional Experience
### Senior Engineer | Global Tech | 2022
• Handled complex systems.
• Optimized cloud operations.
"""

    output_path = Path("test_resume.docx")
    _markdown_to_docx(sample_text, output_path)
    print(f"✅ Generated test DOCX at: {output_path.absolute()}")

if __name__ == "__main__":
    test_docx_gen()
