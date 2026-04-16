# 🤖 Sovereign Agent: Reclaiming the Hiring Process

> **Manifesto**: In an era of automated HR filters and "Ghost Jobs," the job seeker needs a champion. Sovereign Agent is your partner in the chase—a highly intelligent, stealthy assistant that handles the grind so you can focus on the interview.

[![Release](https://img.shields.io/github/v/release/wisdomgreat/JobAutomation?color=blue&label=Latest%20Release)](https://github.com/wisdomgreat/JobAutomation/releases)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Security](https://img.shields.io/badge/Security-100%25%20Local-brightgreen)](#-security--privacy)

---

## 🚀 Quickstart: The Sovereign Desktop App

If you just want to start applyling to jobs, follow these 3 steps:

1.  **Download**: Get the latest **[SovereignAgent.exe here](https://github.com/wisdomgreat/JobAutomation/releases/latest)**.
2.  **Launch**: Double-click the file to open the app.
3.  **Configure**: Our **Onboarding Wizard** will walk you through your setup in 2 minutes.

*For more details, see our full **[Public Launch Guide](PUBLIC_LAUNCH_GUIDE.md)**.*

---

## ✨ Features

- **🧠 Deep Personalization**: We don't spam. Our engine reads every job description and meticulously tailors your resume and cover letter.
- **🥷 Human-Centric Stealth**: Mimics human behavior (randomized scrolling, reading pauses) to protect your professional accounts.
- **📊 Intelligence Dashboard**: Track every mission, view Match Scores, and take control with "Surgical Apply."

---

## 🛡️ Security & Privacy

**Your data stays with you.** Sovereign Agent was built with a "Privacy First" architecture:
- **100% Local**: All resumes, AI configurations, and login details are stored only on your computer.
- **Zero Telemetry**: We do not track your activity, collect your data, or phone home to any external servers.
- **Open Source**: Our security claims are verified by the community. You can audit every line of code.

---

---

## 💻 Developer Setup (PyCharm / VS Code / Terminal)

If the Windows installer is failing due to permissions, or if you prefer to run from source, follow these steps:

### 1. Prerequisites
- **Python 3.10+**: [Download here](https://www.python.org/downloads/) (Ensure "Add Python to PATH" is checked).
- **Git**: [Download here](https://git-scm.com/downloads).

### 2. Setup (Generic Terminal)
```bash
# Clone the repository
git clone https://github.com/wisdomgreat/JobAutomation
cd JobAutomation

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Launch the App
python gui.py
```

### 3. Setting up in PyCharm
1.  **Open Project**: Launch PyCharm and select **Open**. Navigate to the `JobAutomation` folder.
2.  **Configure Interpreter**:
    - Go to `File` > `Settings` > `Project: JobAutomation` > `Python Interpreter`.
    - Click **Add Interpreter** > **Add Local Interpreter**.
    - Select **Virtualenv Environment** and ensure it's creating a new environment in the project folder.
3.  **Install Requirements**: PyCharm will likely detect `requirements.txt` and offer to install them. If not, open the **Terminal** tab at the bottom and run `pip install -r requirements.txt`.
4.  **Run**: Right-click `gui.py` in the project tree and select **Run 'gui'**.

---

## 🤝 Community & Feedback

We are building this for the job seeker. Your feedback drives our roadmap.
- **Spotted a bug?** [Report it here](https://github.com/wisdomgreat/JobAutomation/issues/new?labels=bug).
- **Want a feature?** [Suggest it here](https://github.com/wisdomgreat/JobAutomation/issues/new?labels=enhancement).
- **Need help?** Check the [Wiki](https://github.com/wisdomgreat/JobAutomation/wiki).

---

*Reclaim your career. Automate the grind. Secure the future.*
