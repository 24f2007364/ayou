# Vercel Deployment Instructions

## 🚀 Deploy Your Ayou Platform to Vercel

### Prerequisites
1. A Vercel account (free at [vercel.com](https://vercel.com))
2. Git repository with your code

### Files Added for Vercel Compatibility

1. **`vercel.json`** - Vercel configuration
2. **`index.py`** - Entry point for Vercel
3. **`runtime.txt`** - Python version specification
4. **`.vercelignore`** - Files to exclude from deployment

### Quick Deployment Steps

1. **Push your code to GitHub/GitLab/Bitbucket**

2. **Connect to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Sign up/login with your Git provider
   - Import your repository

3. **Configure Environment Variables:**
   In your Vercel dashboard, add these environment variables:
   ```
   POSTGRES_URL=your-postgres-connection-string-from-vercel-database
   SECRET_KEY=your-super-secure-secret-key-here  
   VERCEL=1
   FLASK_ENV=production
   ```

4. **Deploy:**
   - Click "Deploy"
   - Wait for deployment to complete
   - Your app will be live at `https://your-project-name.vercel.app`

### Important Notes

⚠️ **Database Solution - FIXED!**
- ✅ Now uses **PostgreSQL** for persistent data storage on Vercel
- ✅ Automatically falls back to SQLite for local development
- ✅ Your tools and user accounts will persist between deployments!

**To set up the database:**
1. Add a PostgreSQL database in your Vercel dashboard
2. Copy the `POSTGRES_URL` to your environment variables
3. Deploy - your data will now persist!

⚠️ **File Upload Limitations:**
- Uploaded files are stored in temporary directories
- Files don't persist between requests
- For file storage, consider:
  - **Vercel Blob** (recommended)
  - **AWS S3**
  - **Cloudinary**

### Upgrading to Persistent Database

To use a persistent database, modify `app.py`:

```python
import os
import psycopg2  # for PostgreSQL
from urllib.parse import urlparse

def get_db_connection():
    if os.environ.get('DATABASE_URL'):
        # Use PostgreSQL for production
        url = urlparse(os.environ['DATABASE_URL'])
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
    else:
        # Use SQLite for local development
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
    return conn
```

### Troubleshooting

**If deployment fails:**
1. Check the deployment logs in Vercel dashboard
2. Ensure all required files are present
3. Verify environment variables are set
4. Check Python version compatibility

**If app doesn't work:**
1. Check function logs in Vercel dashboard
2. Ensure database is properly initialized
3. Verify static files are served correctly

### Local Development

To test locally with Vercel CLI:
```bash
npm i -g vercel
vercel dev
```

Your app should now work on Vercel! 🎉
