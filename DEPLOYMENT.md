# Production Deployment Guide

## 🚀 Deploying Your Ayou Platform to Production

### Pre-Deployment Checklist

#### Security Updates
1. **Change Secret Key**
   ```python
   # In app.py, change:
   app.secret_key = 'your-secret-key-change-in-production'
   # To a secure random string:
   app.secret_key = 'your-super-secure-random-key-here'
   ```

2. **Update Admin Password**
   ```python
   # In app.py, change the admin_auth route:
   if password == 'admin123':  # Change this!
   ```

3. **Environment Variables**
   Create a `.env` file:
   ```
   SECRET_KEY=your-super-secure-secret-key
   ADMIN_PASSWORD=your-secure-admin-password
   DATABASE_URL=your-database-url
   FLASK_ENV=production
   ```

#### Code Updates for Production
1. **Update app.py for environment variables**:
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   
   app.secret_key = os.environ.get('SECRET_KEY', 'fallback-key')
   ```

2. **Disable Debug Mode**:
   ```python
   if __name__ == '__main__':
       app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
   ```

## Deployment Options

### 1. Heroku Deployment (Recommended for Beginners)

#### Step 1: Prepare Your App
1. Install Heroku CLI
2. Create additional files:

**Procfile**:
```
web: python app.py
```

**runtime.txt**:
```
python-3.11.0
```

**Updated requirements.txt**:
```
Flask==2.3.3
Werkzeug==2.3.7
gunicorn==21.2.0
python-dotenv==1.0.0
```

#### Step 2: Deploy
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-ai-marketplace

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set ADMIN_PASSWORD=your-admin-password

# Deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main
```

### 2. DigitalOcean Deployment

#### Step 1: Create Droplet
1. Create Ubuntu 20.04 droplet
2. Connect via SSH

#### Step 2: Setup Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv nginx -y

# Create app directory
sudo mkdir /var/www/ai-marketplace
cd /var/www/ai-marketplace

# Upload your files (use scp or git)
git clone your-repository .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 3: Configure Nginx
Create `/etc/nginx/sites-available/ai-marketplace`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /var/www/ai-marketplace/static/;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/ai-marketplace /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 4: Setup Process Manager
Install PM2:
```bash
sudo npm install -g pm2
```

Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [{
    name: 'ai-marketplace',
    script: 'app.py',
    interpreter: '/var/www/ai-marketplace/venv/bin/python',
    cwd: '/var/www/ai-marketplace',
    env: {
      FLASK_ENV: 'production'
    }
  }]
};
```

Start app:
```bash
pm2 start ecosystem.config.js
pm2 startup
pm2 save
```

### 3. AWS EC2 Deployment

#### Step 1: Launch EC2 Instance
1. Choose Amazon Linux 2 AMI
2. Configure security groups (HTTP, HTTPS, SSH)
3. Launch instance

#### Step 2: Setup Application
```bash
# Connect to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install dependencies
sudo yum update -y
sudo yum install python3 python3-pip git -y

# Clone and setup app
git clone your-repository ai-marketplace
cd ai-marketplace
pip3 install -r requirements.txt --user
```

#### Step 3: Run with Gunicorn
```bash
# Install gunicorn
pip3 install gunicorn --user

# Create startup script
echo '#!/bin/bash
cd /home/ec2-user/ai-marketplace
/home/ec2-user/.local/bin/gunicorn -w 4 -b 0.0.0.0:8000 app:app' > start_app.sh

chmod +x start_app.sh
```

## Database Considerations

### SQLite (Current)
- **Pros**: Simple, no setup required
- **Cons**: Not suitable for high traffic
- **Good for**: Small to medium apps

### PostgreSQL (Recommended for Production)
1. Install PostgreSQL
2. Update requirements.txt:
   ```
   psycopg2-binary==2.9.7
   ```
3. Update database connection in app.py

### MySQL Alternative
1. Install MySQL
2. Update requirements.txt:
   ```
   PyMySQL==1.1.0
   ```

## SSL/HTTPS Setup

### Using Let's Encrypt (Free)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Maintenance

### Log Management
1. **Application Logs**: Use Python logging
2. **Server Logs**: Monitor with tools like fail2ban
3. **Error Tracking**: Consider Sentry

### Backup Strategy
1. **Database**: Regular automated backups
2. **Files**: Backup uploaded files
3. **Code**: Use Git for version control

### Performance Optimization
1. **Caching**: Implement Redis for session storage
2. **CDN**: Use for static files
3. **Database**: Add indexes for better performance

## Security Best Practices

### Application Security
1. **Input Validation**: Validate all user inputs
2. **CSRF Protection**: Implement Flask-WTF
3. **Rate Limiting**: Use Flask-Limiter
4. **SQL Injection**: Use parameterized queries (already implemented)

### Server Security
1. **Firewall**: Configure UFW
2. **Fail2Ban**: Protect against brute force
3. **Updates**: Regular security updates
4. **SSH**: Disable password authentication

## Scaling Considerations

### Horizontal Scaling
1. **Load Balancer**: Multiple app instances
2. **Database**: Read replicas
3. **File Storage**: Cloud storage (S3, etc.)

### Vertical Scaling
1. **Memory**: Monitor and increase as needed
2. **CPU**: Scale based on usage
3. **Storage**: Monitor disk usage

## Maintenance Scripts

### Backup Script
```bash
#!/bin/bash
# backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp database.db backups/database_$DATE.db
```

### Update Script
```bash
#!/bin/bash
# update_app.sh
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pm2 restart ai-marketplace
```

## Troubleshooting

### Common Issues
1. **Port in use**: Check with `netstat -tlnp | grep :5000`
2. **Permission denied**: Check file permissions
3. **Database locked**: Ensure only one process accesses SQLite
4. **Static files not loading**: Check Nginx configuration

### Debug Commands
```bash
# Check app status
pm2 status

# View logs
pm2 logs ai-marketplace

# Restart app
pm2 restart ai-marketplace

# Check Nginx status
sudo systemctl status nginx
```

## Final Checklist

- [ ] Updated secret key and admin password
- [ ] Environment variables configured
- [ ] Database backed up
- [ ] SSL certificate installed
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Security measures in place
- [ ] Performance optimization done
- [ ] Documentation updated

## Support Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Deployment Guides**: Check your hosting provider's docs
- **Security Resources**: OWASP guidelines
- **Community**: Stack Overflow, Reddit r/flask

Remember: Always test your deployment in a staging environment first!
