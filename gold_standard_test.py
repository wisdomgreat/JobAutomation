import sys
import os
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import config
from src.resume_builder import generate_documents

def run_gold_standard_test():
    print("🚀 Initializing Sovereign Agent 'Gold Standard' Test...")
    
    # 1. Define a high-quality sample job
    sample_job = {
        "title": "Senior Cloud Infrastructure Architect",
        "company": "Anticorp Global",
        "location": "Toronto, ON (Remote)",
        "description": """
        We are seeking an elite Senior Cloud Architect to lead our digital transformation. 
        Requirements:
        - 15+ years of IT experience with deep expertise in Microsoft 365, Azure, and Identity Management.
        - Proven track record of architecting secure, scalable cloud solutions.
        - Experience with ServiceNow, Jira, and enterprise-scale deployments.
        - Strong leadership skills and ability to present to stakeholders.
        """
    }

    # 2. Cleanup previous test outputs to avoid confusion
    test_dir = Path("test_output")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    print(f"📄 Target: {sample_job['title']} @ {sample_job['company']}")
    
    try:
        # 3. Generate the full suite
        paths = generate_documents(
            job_title=sample_job["title"],
            company=sample_job["company"],
            location=sample_job["location"],
            job_description=sample_job["description"]
        )
        
        # 4. Copy generated files to test_output for easy access
        print("\n✨ Mission Successful! Assets Generated:")
        for key, path in paths.items():
            if key == "output_dir": continue
            dest = test_dir / path.name
            shutil.copy(path, dest)
            print(f"  ✅ {key.replace('_', ' ').title()}: {dest}")
            
        print(f"\n📂 All files are ready for verification in: {test_dir.absolute()}")
        print("💡 Open these files now to see the premium headers and hardened formatting!")

    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_gold_standard_test()
