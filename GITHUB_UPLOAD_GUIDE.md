# GitHub Upload Guide

## Quick Start (5 Steps)

### 1. Initialize Git Repository
```bash
cd /Users/zuotongzhang/projects/sahra_rag_demo
git init
git add .
git commit -m "Initial commit: SahraEvent RAG Demo with LangGraph"
```

### 2. Create GitHub Repository
1. Go to [GitHub](https://github.com) and log in
2. Click the **+** icon (top right) → **New repository**
3. Fill in details:
   - **Repository name:** `sahra-rag-demo` (or your preferred name)
   - **Description:** "Fast, reliable RAG system for event venue recommendations using LangGraph and BM25"
   - **Visibility:** Choose Public or Private
   - ⚠️ **DO NOT** check "Initialize with README" (we already have one)
4. Click **Create repository**

### 3. Connect Local to GitHub
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/sahra-rag-demo.git
git branch -M main
```

### 4. Push to GitHub
```bash
git push -u origin main
```

### 5. Verify
- Open your repository URL: `https://github.com/YOUR_USERNAME/sahra-rag-demo`
- You should see all your files!

---

## What Gets Uploaded

### ✅ Included:
- All Python code (`app.py`, `rag/*.py`)
- Documentation (`README.md`, `DEMO_GUIDE.md`, `DEMO_CHEAT_SHEET.md`)
- Sample data (`data/vendors.csv`)
- Dependencies (`requirements.txt`)
- License (if you add one)

### ❌ Excluded (via `.gitignore`):
- `__pycache__/` (Python cache)
- `.env` (API keys - **important!**)
- `sahra.db` (database - regenerated on run)
- `.vscode/`, `.idea/` (IDE settings)
- Virtual environment folders

---

## Important: Protect Your API Key

### ⚠️ Never commit `.env` file!

Your OpenAI API key should **never** be in Git. Instead:

1. **Local development:** Use `.env` file (already in `.gitignore`)
   ```bash
   # .env file (not committed)
   OPENAI_API_KEY=sk-proj-...
   ```

2. **For other users:** Document in README
   ```markdown
   ## Setup
   1. Clone this repository
   2. Create `.env` file:
      ```
      OPENAI_API_KEY=your_key_here
      ```
   3. Run `streamlit run app.py`
   ```

3. **For deployment:** Use environment variables in hosting platform

---

## Step-by-Step Terminal Commands

Run these commands in order:

```bash
# 1. Navigate to project
cd /Users/zuotongzhang/projects/sahra_rag_demo

# 2. Check git status (should show untracked files)
git status

# 3. Add all files
git add .

# 4. Check what will be committed
git status

# 5. Commit with descriptive message
git commit -m "Initial commit: SahraEvent RAG Demo

- LangGraph pipeline with 4 checkpoints
- BM25 hybrid search with vendor deduplication
- Smart caching (6h query, 24h completion)
- Staleness detection (14-day threshold)
- Natural language slot extraction
- Citation-enforced responses
- Cost-optimized model routing (~$0.002/query)"

# 6. Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/sahra-rag-demo.git

# 7. Rename branch to main (GitHub standard)
git branch -M main

# 8. Push to GitHub
git push -u origin main
```

---

## Alternative: Using GitHub Desktop

If you prefer a GUI:

1. Download [GitHub Desktop](https://desktop.github.com)
2. Open GitHub Desktop
3. Click **File** → **Add Local Repository**
4. Select `/Users/zuotongzhang/projects/sahra_rag_demo`
5. Click **Publish repository**
6. Choose name and visibility
7. Click **Publish**

---

## Add a License (Optional but Recommended)

### MIT License (Most permissive):
```bash
# Create LICENSE file
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# Add and commit
git add LICENSE
git commit -m "Add MIT License"
git push
```

---

## Improve Your GitHub Presence

### Add Topics/Tags
On your GitHub repo page:
1. Click ⚙️ Settings icon (top right, near About)
2. Add topics: `rag`, `langchain`, `langgraph`, `streamlit`, `bm25`, `llm`, `gpt-4`, `event-planning`, `search-engine`

### Add Badges to README
Add at the top of `README.md`:
```markdown
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.38-red.svg)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/langgraph-0.2.33-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

### Add a Screenshot
1. Run your app: `streamlit run app.py`
2. Take a screenshot of the UI
3. Save as `screenshot.png` in project root
4. Add to README:
   ```markdown
   ## Demo
   ![SahraEvent RAG Demo](screenshot.png)
   ```
5. Commit and push:
   ```bash
   git add screenshot.png README.md
   git commit -m "Add demo screenshot"
   git push
   ```

---

## Future Updates

When you make changes:

```bash
# 1. Check what changed
git status

# 2. Add changed files
git add .

# 3. Commit with message
git commit -m "Description of changes"

# 4. Push to GitHub
git push
```

---

## Troubleshooting

### "Permission denied (publickey)"
**Solution:** Use HTTPS URL instead of SSH:
```bash
git remote set-url origin https://github.com/YOUR_USERNAME/sahra-rag-demo.git
```

### "Authentication failed"
**Solution:** Use Personal Access Token:
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Use token as password when pushing

### "Large files detected"
**Solution:** Git doesn't like files >100MB. If you have large model files:
```bash
# Install Git LFS
brew install git-lfs  # macOS
git lfs install

# Track large files
git lfs track "*.bin"
git lfs track "*.pt"
git add .gitattributes
git commit -m "Add Git LFS tracking"
git push
```

### "Nothing to commit"
**Solution:** Check `.gitignore` isn't excluding needed files:
```bash
git status --ignored
```

---

## Make Your Repo Discoverable

### Good README Structure
Your current README is excellent! It has:
- ✅ Clear title and description
- ✅ Features list
- ✅ Quick start guide
- ✅ Usage examples
- ✅ Project structure
- ✅ Technical details
- ✅ Implementation status

### Add a Star ⭐
- Star your own repo to boost visibility
- Share with colleagues/friends

### Write a Blog Post
- Write about your implementation on Medium, Dev.to, or LinkedIn
- Link to your GitHub repo
- Tag relevant topics

---

## Deployment Options

Once on GitHub, you can deploy:

### Streamlit Cloud (Easiest)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select your repo
4. Add secrets (OPENAI_API_KEY) in Streamlit Cloud settings
5. Deploy!

### Heroku
```bash
# Add Procfile
echo "web: streamlit run app.py --server.port=$PORT" > Procfile
git add Procfile
git commit -m "Add Heroku Procfile"
git push
```

### Docker
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

---

## Security Checklist

Before pushing to public repo:

- [ ] `.env` file is in `.gitignore`
- [ ] No API keys in code
- [ ] No hardcoded passwords
- [ ] No sensitive data in `data/vendors.csv`
- [ ] Database file (`sahra.db`) in `.gitignore`
- [ ] Test with fresh clone to ensure it works

---

## GitHub Best Practices

1. **Write good commit messages**
   - Bad: "fix stuff"
   - Good: "Fix: Vendor deduplication for wedding venues in Abu Dhabi"

2. **Commit frequently**
   - Don't wait until everything is perfect
   - Commit working features incrementally

3. **Use branches for experiments**
   ```bash
   git checkout -b feature/add-faiss-search
   # make changes
   git commit -m "Add FAISS dense search"
   git push -u origin feature/add-faiss-search
   # Create pull request on GitHub
   ```

4. **Keep README updated**
   - Update when adding features
   - Document breaking changes

---

## Next Steps After Upload

1. ✅ Upload to GitHub (you're doing this now!)
2. 📱 Share on social media (LinkedIn, Twitter)
3. 📊 Add GitHub Actions for CI/CD (optional)
4. 🚀 Deploy to Streamlit Cloud for live demo
5. 📝 Write technical blog post
6. 🎥 Record demo video
7. 💼 Add to your portfolio

Good luck! 🚀

