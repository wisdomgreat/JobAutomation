# Sovereign Agent: User Manual (v30.11.0)

Welcome to Sovereign Agent! This guide will walk you through setting up and using your personal AI job assistant. Our goal is to make the repetitive parts of job hunting effortless, so you can focus on acing your interviews.

---

## 1. Privacy First

Your privacy is our top priority:
* **Local Storage**: Your resume, AI API keys, and account passwords never leave your computer. Everything is stored locally.
* **No Tracking**: We don't track your usage or collect your data.
* **Open Source**: The code is completely public and transparent, so anyone can verify how it works.

---

## 2. Installation

### Windows Users (Recommended)

We offer two easy ways to run the app on Windows without needing to install programming tools.

#### Option A: The Installer (.exe) - *Easiest!*
1. Go to the [Releases page](https://github.com/wisdomgreat/JobAutomation/releases/latest) and download `Sovereign_Agent_Setup_30.11.0.exe`.
2. Double-click the downloaded file and follow the standard installation prompts.
3. Open "Sovereign Agent" from your Start menu!

#### Option B: Portable Version (.zip)
1. Download `SovereignAgent_Portable_v30.11.0.zip` from the Releases page.
2. Extract the folder to your computer (e.g., your Desktop or Documents folder).
3. Inside the folder, double-click `SovereignAgent_Portable.exe` to run the app.

### Mac and Linux Users (Source Code)

For macOS and Linux, you'll need to run the app from its source code.
1. Open your Terminal.
2. Ensure you have Python 3.10+ installed.
3. Run the following commands:
   ```bash
   git clone https://github.com/wisdomgreat/JobAutomation.git
   cd JobAutomation
   pip3 install -r requirements.txt
   python3 main.py
   ```

---

## 3. How to Update the App

We frequently release new features and bug fixes. To update your app to the latest version:

### If using the Installer or Portable (.zip)
1. Go to our [Releases page](https://github.com/wisdomgreat/JobAutomation/releases/latest).
2. Download the newest Installer (`.exe`) or Portable zip.
3. Run the installer or extract the zip. Your data (like your resume and profile) is saved securely in your AppData folder, so **you will not lose your saved information** when you update!

### If using Source Code
Simply open your terminal, go to the `JobAutomation` folder, and type:
```bash
git pull
```

---

## 4. Getting Started: The Setup Checklist


When you first open Sovereign Agent, some features will be locked until you complete a quick setup. Follow these steps to get everything ready:

### A. Connect Your AI
The app uses an AI (like ChatGPT or Claude) to read job descriptions and write your custom cover letters and resumes.

1. Go to the **🧠 INTELLIGENCE** tab on the left menu.
2. Choose your preferred AI provider (e.g., OpenAI, Anthropic, or OpenRouter for affordable options).
3. Paste your API key into the secure password box.
4. Click **🧪 TEST CONNECTION** to make sure it's working!

### B. Fill Out Your Profile
Tell the app about your experience so it can fill out job applications for you.

1. Go to the **⚙️ SYSTEM CORE** tab.
2. Click **📝 LAUNCH PROFILE EDITOR**.
3. Fill out the tabs: Personal Info, Work Experience, Salary Preferences, and Skills.
4. Click **💾 SAVE PROFILE** when you're done.

### C. Upload Your Base Resume
The AI needs your standard resume to learn about your background.

1. Go to the **📂 ASSET HUB** tab.
2. Click to upload your current resume (PDF or Word document).
3. The app will save a copy locally to use as a template for tailoring.

---

## 5. How to Find and Apply for Jobs

Sovereign Agent gives you several powerful tools to find work.

### Automated Job Searching
Let the app scan job boards for you and automatically apply to the best matches.

1. Go to the **🔍 TARGET SCAN** tab.
2. Enter the **Job Title** (e.g., "Software Engineer") and **Location** (e.g., "Remote" or "New York").
3. Check the boxes for the sites you want to search (LinkedIn, Indeed, etc.).
4. Click **⚡ START SEARCH**. 
5. The new **Antigravity Browsing Engine (AABE)** will safely open background browsers to find jobs and add them to your tracker.

### The Application Tracker (CRM)
Track every job you find in one easy place!

1. Go to the **🤝 APPLICATION TRACKER** tab to see your list of jobs.
2. The app assigns a **Match Score (0-100%)** to show how well your resume fits the job.
3. Click **APPLY** next to any job. The app will instantly generate a tailored resume and cover letter, and attempt to fill out the application form for you!
4. You can also manually mark jobs as "Interviewing", "Rejected", or delete them to keep your list clean.

### Direct Job Link Apply
Found a job link on your own? The app can still tailor your resume for it!

1. Go to the **🔍 TARGET SCAN** tab.
2. Paste the URL of the job posting into the "Direct Link" box.
3. Click **🚀 APPLY TO LINK**.

---

## 6. Advanced Features

### Safety First (Stealth Mode)
To keep your LinkedIn and Indeed accounts safe from being flagged as bots, the app uses "Stealth Mode." It scrolls and clicks at human speeds with randomized pauses. We highly recommend keeping this feature turned on in your settings!

### Email Alert Scanning
If you get job alerts sent to your email (like Yahoo, Gmail, or Outlook), Sovereign Agent can read them for you!
1. Go to the **🧠 INTELLIGENCE** tab to set up your email provider. (You will usually need to generate an "App Password" from your email settings).
2. Go to **🔍 TARGET SCAN** and click **🔍 SCAN EMAILS** to automatically pull those jobs into your tracker.

---

## 7. FAQ & Troubleshooting

### Is it safe to use this on my LinkedIn account?
Yes! The Antigravity Browsing Engine uses safe, human-like scrolling and randomized clicking delays to ensure your account isn't flagged. However, we always recommend avoiding running thousands of applications in a single day. 

### Why is my Application Tracker empty?
The tracker usually defaults to showing "New" jobs. If you haven't searched for any jobs yet, it will be empty! Head over to the Target Scan tab to find some jobs.

### I'm getting an error when I try to run a search.
1. Check your internet connection.
2. Ensure you aren't using a strict VPN that job boards might block.
3. Check the log screen on the Dashboard to see what the specific error says.

### Need more help?
If you're stuck, feel free to open an issue on our GitHub page or ask the community for support! Happy job hunting!
