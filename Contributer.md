# 🛠️ Working on `fix/Hide_update_daily` Branch – Contributor Guide

This guide explains how to work on the branch `fix/Hide_update_daily` safely, from cloning the repository to creating a pull request without affecting the production code.

---

## ✅ Step-by-Step Instructions

### 1. Clone the Repository (If not already cloned)

```bash
git clone https://github.com/your-username/ai-exchange.git
cd ai-exchange
```

### 2. Fetch All Branches

```bash
git fetch --all
```

### 3. Checkout the `dev` Branch

```bash
git checkout dev
git pull origin dev
```

### 4. Checkout the `fix/Hide_update_daily` Branch

If it already exists locally:

```bash
git checkout fix/Hide_update_daily
```



## 5. Make Code Changes

Make the necessary fix (e.g., hide the "Update Daily" info on the leaderboard page).

### 6. Stage and Commit Changes

```bash
git add .
git commit -m "Fix: hide update daily info from leaderboard page"
```

### 7. Push the Branch to GitHub

```bash
git push origin fix/Hide_update_daily
```

### 8. Create a Pull Request (PR)

1. Go to your GitHub repository in the browser.
2. Click on **"Compare & pull request"**.
3. Confirm the base is `dev` and compare is `fix/Hide_update_daily`.
4. Add a short description of the fix.
5. Click **Create Pull Request**.

---

## 🔁 After the PR

* Wait for review and approval.
* Once tested on Vercel Preview, the PR will be merged into `dev`.
* When everything is ready in `dev`, it will be merged into `main` for production deployment.

---

## 🔁 Quick Command Recap

```bash
git clone https://github.com/your-username/ai-exchange.git
cd ai-exchange
git fetch --all
git checkout dev
git pull origin dev
git checkout -b fix/Hide_update_daily origin/fix/Hide_update_daily

# Make your changes
git add .
git commit -m "Fix: hide update daily info from leaderboard page"
git push origin fix/Hide_update_daily
```
