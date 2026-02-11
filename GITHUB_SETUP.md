# How to create GitHub and send the link (full steps)

Do these in order.

---

## Step 1: GitHub account (if you don’t have one)

1. Open: **https://github.com**
2. Click **Sign up**
3. Enter email, password, username. Verify email if asked.
4. Remember your **username** — you’ll need it later.

---

## Step 2: Tell Git who you are (one time per PC)

Open **PowerShell** or **Command Prompt** and run (use your real name and the email you use on GitHub):

```powershell
git config --global user.email "your.email@example.com"
git config --global user.name "Your Name"
```

Example:  
`git config --global user.email "alice@gmail.com"`  
`git config --global user.name "Alice"`

---

## Step 3: Make the first commit in your project

In PowerShell:

```powershell
cd C:\Users\Alice\minimus-qa
git add -A
git commit -m "Minimus QA: pytest suite for PostgreSQL image (BUG-02, 03, 04, 06)"
```

You should see something like: `X files changed`, `create mode 100644 ...`

---

## Step 4: Create an empty repository on GitHub

1. Go to: **https://github.com/new**
2. **Repository name:** type `minimus-qa` (or another name you like).
3. **Description (optional):** e.g. `Pytest tests for Minimus PostgreSQL image`.
4. **Public** — leave this selected.
5. **Do NOT** check “Add a README file” (your project already has one).
6. Click **Create repository**.

You’ll see a page that says “Quick setup” and shows a URL like  
`https://github.com/YOUR_USERNAME/minimus-qa.git`  
Keep this page open.

---

## Step 5: Connect your folder to GitHub and push

In PowerShell, from your project folder:

```powershell
cd C:\Users\Alice\minimus-qa
git remote add origin https://github.com/YOUR_USERNAME/minimus-qa.git
git branch -M main
git push -u origin main
```

- Replace **YOUR_USERNAME** with your real GitHub username (e.g. if your username is `alice2024`, the URL is `https://github.com/alice2024/minimus-qa.git`).

When you run `git push`:

- If it asks for **username**: your GitHub username.
- If it asks for **password**: do **not** use your GitHub password. Use a **Personal Access Token**:
  1. GitHub → your profile (top right) → **Settings**
  2. Left sidebar: **Developer settings** → **Personal access tokens** → **Tokens (classic)**
  3. **Generate new token (classic)**. Name it e.g. “minimus-qa”. Check **repo**.
  4. **Generate token**. Copy the token (you won’t see it again).
  5. When Git asks for password, paste this token.

After a successful push, the page on GitHub will show your files (README, conftest.py, test_helm_bugs.py, etc.).

---

## Step 6: Send the link to your interviewer

Your repository URL is:

**https://github.com/YOUR_USERNAME/minimus-qa**

(Again, replace YOUR_USERNAME with your username.)

Send them this link. They can clone the repo and follow the **Quick Start** in your README to run the tests.

---

## Quick checklist

- [ ] GitHub account created
- [ ] `git config` name and email set
- [ ] `git commit` done in `C:\Users\Alice\minimus-qa`
- [ ] New repo created at github.com/new (no README)
- [ ] `git remote add origin ...` and `git push` done
- [ ] Link copied and sent to interviewer
