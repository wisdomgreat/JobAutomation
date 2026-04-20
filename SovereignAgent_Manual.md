# Sovereign Agent: Complete Operations Manual

## 1. Overview and Manifesto
In the contemporary landscape of automated HR filters and "Ghost Jobs," the job seeker requires a technological advantage. Sovereign Agent serves as a highly intelligent, localized automation engine designed to handle the repetitive aspects of the job application process, allowing the user to focus on interview preparation and career strategy.

## 2. Security and Privacy Policy
Privacy is a fundamental component of the Sovereign Agent architecture.
* **Localized Storage**: All resumes, AI configurations, and authentication credentials are stored exclusively on the user's local machine.
* **No Telemetry**: The system does not collect data or communicate with external servers beyond the specified AI providers and job platforms.
* **Auditability**: As an open-source project, the codebase is fully transparent and available for security auditing.

## 3. System Requirements and Installation

### Windows Installation
Windows users may choose between a portable executable or running from the source code.

#### Option A: Portable Executable (Recommended)
1. Download the latest `SovereignAgent_Portable.zip` from the official repository releases.
2. Extract the contents to a dedicated directory (e.g., `C:\SovereignAgent`).
3. Execute `SovereignAgent_Portable.exe` to launch the application.

#### Option B: Installation from Source
1. Install Git from git-scm.com.
2. Install Python 3.10+ from Python.org, ensuring the "Add Python to PATH" option is selected.
3. Open a terminal and execute the following commands:
   ```cmd
   git clone https://github.com/wisdomgreat/JobAutomation
   cd JobAutomation
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python gui.py
   ```

### macOS Installation
macOS requires execution from the source code via the Terminal.
1. Install Homebrew:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install dependencies:
   ```bash
   brew install git python3
   ```
3. Execute the setup:
   ```bash
   git clone https://github.com/wisdomgreat/JobAutomation
   cd JobAutomation
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   python3 gui.py
   ```

### Linux and Unix Installation
1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install git python3 python3-pip python3-venv xvfb
   ```
2. Execute the setup:
   ```bash
   git clone https://github.com/wisdomgreat/JobAutomation
   cd JobAutomation
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 gui.py
   ```

## 4. Post-Installation Configuration

### Initial Launch and Mandatory Onboarding
Upon the first execution, the Sovereign Agent enters a locked state. The Dashboard and Scanning features will only activate once the "Mission Readiness" parameters (AI keys, Identity, and Resume) are satisfied.

### AI Engine Configuration
The system relies on a Large Language Model (LLM) to parse job descriptions and generate tailored content.
1. **Navigate to System Core**: Click the gear icon in the sidebar.
2. **Select Provider**:
   * **OpenAI**: High reliability and standard performance. Requires an OpenAI API key.
   * **Anthropic**: Excellent for nuanced writing and complex analysis.
   * **OpenRouter**: Highly recommended for optimized costs. Provides access to various models (Claude, LLama, GPT) through a single interface.
3. **Select Model**:
   * **gpt-4o / claude-3-sonnet**: High intelligence for complex tailoring.
   * **gpt-4o-mini**: Fast and highly cost-effective for bulk processing.
4. **Credential Entry**: Paste the API Key and select **SAVE KEY**.
5. **Validation**: Select **Test AI Synapse**. A successful handshake will display a green confirmation alert in the console.

### Identity Commander Setup
Setting your identity is critical for accurate tailoring.
1. **Access Identity**: Within the System Core tab, select **EDIT GLOBAL IDENTITY**.
2. **Personal Information**: Provide your full name, contact information, and professional summary.
3. **Strategic Preferences**:
   * **Target Roles**: Enter the specific titles you are seeking (e.g., Senior DevOps Engineer).
   * **Match Sensitivity**: Adjust the slider to determine how strictly the AI should filter jobs. A higher sensitivity (e.g., 85%) will ignore less relevant postings.
4. **Save**: Click **SAVE IDENTITY** to commit the profile to the local encrypted database.

### Asset Hub and Master Resume
The AI uses your "Master Resume" as the source of truth for all career data.
1. **Navigate to Asset Hub**.
2. **Upload Primary Resume**: Select your current resume (PDF or DOCX).
3. **Verification**: The system will confirm successful ingestion. This document is archived locally and used to generate tailored variants for every application.

### Behavioral Stealth Configuration
To protect your accounts on LinkedIn and Indeed, the agent includes human-mimicry protocols.
1. **Stealth Mode Toggle**: Ensure this is enabled in the Dashboard.
2. **Pausing**: The agent will introduce randomized "reading" pauses (5-15 seconds) and scroll behavior to emulate a human user.
3. **Headless Execution**: For a faster (but more detectable) experience, headless mode can be toggled; however, it is recommended to keep this disabled for primary account safety.

## 5. Operational Procedures

### Automated Job Scanning
1. **Search Matrix**: Define the "Job Title" and "Location" (e.g., "Remote" or "London").
2. **Select Targets**: Check the boxes for the desired job boards.
3. **Initiate**: Select **RUN FULL AUTO-PIPELINE**.
4. **Monitoring**: The system will sync discovered jobs every 5 minutes while the engine is active.

### Candidate CRM Management
1. **Review Feed**: Discovered jobs appear in the CRM.
2. **Match Score**: Review the AI-calculated score.
3. **Actions**:
   * **Quick Apply**: Generates a tailored resume and cover letter instantly.
   * **Open Output**: Access the generated files in the `output/` directory.
   * **Mark Applied**: Select the checkmark icon to log the application and clear it from the active queue.

## 6. Advanced Configuration: Email Integration
The Email Scanner parses incoming job alerts from Gmail, Yahoo, or Outlook.
1. **Enable App Passwords**: Your primary email password will not work for security reasons. Generate a 16-character "App Password" via your email provider's security settings.
2. **Configure Security Tab**: Enter the email address and App Password in the corresponding platform tab.
3. **Run Scan**: The agent will extract direct job links from your email notifications and add them as targets in the CRM.

## 7. Frequently Asked Questions (FAQ)

### Is using this bot safe for my LinkedIn account?
Yes. The Sovereign Agent is designed with behavioral offsets. It avoids rapid-fire actions, implements human scrolling patterns, and does not interact with protected API endpoints directly. However, it is always recommended to use the "Stealth Mode" settings for maximum safety.

### Why is the Candidate CRM feed empty?
The CRM feed defaults to showing "NEW" jobs. If you have already applied to or dismissed all targets, the feed will appear empty. Ensure your search parameters (Title/Location) are broad enough to yield results.

### Which AI model provides the best value?
**gpt-4o-mini** via OpenRouter is currently the most cost-effective solution, providing high-quality tailoring for cent-fractions per application.

### Does the system support remote-only searches?
Yes. Simply input "Remote" or "Work from Home" into the Location field of the Search Matrix.

## 8. Troubleshooting Guide

### Application Crash on Launch (Windows)
If the application crashes immediately with a `TclError`, ensure you are using the latest version (v30.2.2+). This is a known compatibility issue with Windows 11 title bar rendering which has been patched in recent updates.

### "No Update Available" Error
If clicking the "Sync System Code" button results in an error message despite an update being available, manually restart the application or download the latest portable version from the GitHub releases page.

### Search Engine Failing to Extract Jobs
If the Live Console shows "0 targets found" repeatedly:
1. Verify your internet connection.
2. Ensure you do not have a VPN active that is blocked by job platforms.
3. Check the "Manual Matrix" in the Scan tab to see if a manual browser session can access the site.

### API Key Rejected
Ensure there are no leading or trailing spaces in your API key. Test the key using the "Test AI Synapse" button; if it fails, check your balance on the provider's billing dashboard (OpenAI/OpenRouter).

### Documentation and Support
For persistent issues, utilize the repository's issues tracker or join the discussion board for community assistance.
