# Database Configuration Guide

## 🔧 **Two Configuration Options**

### **Option 1: DATABASE_URL (Recommended for Production)**

Use this for cloud databases like Supabase, Heroku, or other production environments:

```env
# .env file
DATABASE_URL=postgresql://postgres:your_password@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

**Advantages:**
- ✅ Single environment variable
- ✅ Standard format for cloud platforms
- ✅ Automatic SSL configuration
- ✅ Easy deployment

### **Option 2: Individual Parameters (For Local Development)**

Use this for local PostgreSQL installations:

```env
# .env file
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rwa_chatbot
DB_USER=rwa_bot
DB_PASSWORD=your_secure_password_here
```

**Advantages:**
- ✅ More explicit configuration
- ✅ Easy to understand individual settings
- ✅ Good for development environments

## 🚀 **For Supabase Users**

1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **Database**
3. Copy the **Connection string** from the **Connection Info** section
4. Add it to your `.env` file as `DATABASE_URL`

Example:
```env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

## 🔍 **Configuration Validation**

The improved `setup_database.py` will:

- ✅ **Validate DATABASE_URL format** if provided
- ✅ **Fallback to individual parameters** if DATABASE_URL not found
- ✅ **Check for placeholder values** and warn you
- ✅ **Test connection** before proceeding
- ✅ **Show configuration summary** after setup

## 🧪 **Testing Your Configuration**

```bash
# Test your database configuration
python setup_database.py
```

This will show you:
- Which configuration method is being used
- Connection test results
- Setup progress
- Configuration summary

## ⚠️ **Important Notes**

1. **Choose ONE method** - Don't use both DATABASE_URL and individual parameters
2. **Update placeholder values** - Replace all `your_*` placeholders with actual values
3. **Keep credentials secure** - Never commit your `.env` file to version control
4. **Test before proceeding** - Always run `setup_database.py` first

## 🎯 **Quick Start**

1. **Copy template**: `cp .env.template .env`
2. **Choose configuration method** (DATABASE_URL or individual parameters)
3. **Update credentials** with your actual values
4. **Test setup**: `python setup_database.py`
5. **Continue with**: `python index_site.py`
