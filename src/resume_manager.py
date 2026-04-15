import os
import shutil
from pathlib import Path
import config

RESUME_DIR = config.DATA_DIR / "resumes"
RESUME_DIR.mkdir(parents=True, exist_ok=True)

class ResumeManager:
    """Manages multiple resume versions for A/B testing and role targeting."""
    
    def __init__(self):
        self.resumes = self.list_resumes()

    def list_resumes(self):
        """List all available PDF resumes in the resumes folder."""
        return list(RESUME_DIR.glob("*.pdf"))

    def get_best_resume(self, job_title: str, job_description: str = "") -> Path:
        """
        Smart-select the best resume based on the job title.
        Fallback to 'standard.pdf' or the first one found.
        """
        all_resumes = self.list_resumes()
        if not all_resumes:
            return None
            
        # 1. Simple Keyword Match in Filename
        # If job title contains 'Manager' and we have 'Resume_Manager.pdf', pick it.
        title_lower = job_title.lower()
        for res in all_resumes:
            # Check if any part of the filename (excluding extension) matches job title
            keyword = res.stem.lower().replace("resume_", "").replace("_", " ")
            if keyword in title_lower:
                return res
                
        # 2. Priority Fallback
        # Look for 'standard.pdf' or 'main.pdf'
        for res in all_resumes:
            if res.stem.lower() in ["standard", "main", "primary"]:
                return res
        
        # 3. Absolute Fallback
        return all_resumes[0]

    def add_resume(self, source_path: str, alias: str):
        """Add a new resume version to the local vault."""
        target = RESUME_DIR / f"resume_{alias.replace(' ', '_')}.pdf"
        shutil.copy(source_path, target)
        return target
