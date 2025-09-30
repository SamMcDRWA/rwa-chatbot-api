# n8n Integration Guide for RWA Chatbot News

This guide shows you how to connect your n8n news aggregation workflow to the RWA Chatbot.

## 🎯 **Integration Overview**

Your n8n workflow will send news articles to the chatbot via a webhook endpoint, which stores them in the PostgreSQL database for display in the news sidebar.

## 🔧 **Setup Steps**

### **Step 1: Database Table Created ✅**
The `chatbot.news_articles` table has been created with the following structure:
- `id` - Primary key
- `title` - Article title
- `summary` - Article summary
- `content` - Full article content
- `url` - Article URL
- `source` - News source (e.g., "PharmacyBiz", "NHS", "CPE")
- `category` - Article category (e.g., "Regulations", "Technology")
- `published_date` - When the article was published
- `created_at` - When stored in database
- `updated_at` - Last updated timestamp
- `is_active` - Whether article is active (default: true)

### **Step 2: Webhook Endpoint Available ✅**
Your chatbot now has a webhook endpoint at:
```
POST http://localhost:8000/news/webhook
```

### **Step 3: Configure n8n Workflow**

#### **Option A: HTTP Request Node (Recommended)**

1. **Add HTTP Request Node** to your n8n workflow
2. **Configure the node:**
   - **Method**: POST
   - **URL**: `http://localhost:8000/news/webhook`
   - **Headers**: 
     ```json
     {
       "Content-Type": "application/json"
     }
     ```
   - **Body**: 
     ```json
     {
       "article": {
         "title": "{{ $json.title }}",
         "summary": "{{ $json.summary }}",
         "content": "{{ $json.content }}",
         "url": "{{ $json.url }}",
         "source": "{{ $json.source }}",
         "category": "{{ $json.category }}",
         "published_date": "{{ $json.published_date }}"
       }
     }
     ```

#### **Option B: Multiple Articles (Batch Processing)**

If your n8n workflow processes multiple articles, you can:

1. **Use a Loop** to send each article individually
2. **Or modify the webhook** to accept arrays (contact us for this option)

## 📊 **Expected Data Format**

Your n8n workflow should send data in this format:

```json
{
  "article": {
    "title": "New Pharmacy Regulations Announced",
    "summary": "The latest updates to pharmacy regulations have been published...",
    "content": "Full article content here...",
    "url": "https://pharmacybiz.com/article/123",
    "source": "PharmacyBiz",
    "category": "Regulations",
    "published_date": "2024-01-15T10:30:00Z"
  }
}
```

## 🔄 **Workflow Integration Examples**

### **Example 1: Single Article Processing**

```json
{
  "nodes": [
    {
      "name": "RSS Feed",
      "type": "n8n-nodes-base.rssFeedRead",
      "parameters": {
        "url": "https://pharmacybiz.com/rss"
      }
    },
    {
      "name": "Process Article",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Process and format article data\nreturn {\n  title: $input.first().json.title,\n  summary: $input.first().json.description,\n  content: $input.first().json.content,\n  url: $input.first().json.link,\n  source: 'PharmacyBiz',\n  category: 'General',\n  published_date: $input.first().json.pubDate\n};"
      }
    },
    {
      "name": "Send to Chatbot",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/news/webhook",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "article": "={{ $json }}"
        }
      }
    }
  ]
}
```

### **Example 2: Multiple Sources**

```json
{
  "nodes": [
    {
      "name": "PharmacyBiz RSS",
      "type": "n8n-nodes-base.rssFeedRead",
      "parameters": {
        "url": "https://pharmacybiz.com/rss"
      }
    },
    {
      "name": "NHS RSS",
      "type": "n8n-nodes-base.rssFeedRead", 
      "parameters": {
        "url": "https://www.england.nhs.uk/feed/"
      }
    },
    {
      "name": "Merge Sources",
      "type": "n8n-nodes-base.merge",
      "parameters": {
        "mode": "append"
      }
    },
    {
      "name": "Process Each Article",
      "type": "n8n-nodes-base.splitInBatches",
      "parameters": {
        "batchSize": 1
      }
    },
    {
      "name": "Format Article",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Determine source and format\nconst url = $input.first().json.link || '';\nlet source = 'Unknown';\nlet category = 'General';\n\nif (url.includes('pharmacybiz')) {\n  source = 'PharmacyBiz';\n  category = 'Industry News';\n} else if (url.includes('nhs')) {\n  source = 'NHS';\n  category = 'Policy';\n}\n\nreturn {\n  title: $input.first().json.title,\n  summary: $input.first().json.description,\n  content: $input.first().json.content,\n  url: url,\n  source: source,\n  category: category,\n  published_date: $input.first().json.pubDate\n};"
      }
    },
    {
      "name": "Send to Chatbot",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/news/webhook",
        "headers": {
          "Content-Type": "application/json"
        },
        "body": {
          "article": "={{ $json }}"
        }
      }
    }
  ]
}
```

## 🧪 **Testing the Integration**

### **Test 1: Manual Webhook Test**

```bash
curl -X POST http://localhost:8000/news/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "article": {
      "title": "Test Article",
      "summary": "This is a test article from n8n",
      "content": "Full test content here",
      "url": "https://example.com/test",
      "source": "Test Source",
      "category": "Test",
      "published_date": "2024-01-15T10:30:00Z"
    }
  }'
```

### **Test 2: Check News Endpoint**

```bash
curl http://localhost:8000/news
```

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **Connection Refused**: Make sure your chatbot API is running on port 8000
2. **Database Error**: Check your DATABASE_URL environment variable
3. **No Articles Showing**: Check if articles are being stored in the database

### **Debug Steps:**

1. **Check API Logs**: Look at the chatbot API console for webhook calls
2. **Check Database**: Query the `chatbot.news_articles` table directly
3. **Test Webhook**: Use the manual test above to verify the endpoint works

## 📈 **Advanced Features**

### **Article Deduplication**
The system can be enhanced to prevent duplicate articles by checking URLs or titles.

### **Article Expiration**
Articles can be automatically marked as inactive after a certain period.

### **Category Filtering**
The news sidebar can be enhanced to filter by category or source.

## 🚀 **Next Steps**

1. **Configure your n8n workflow** using the examples above
2. **Test the integration** with the manual webhook test
3. **Monitor the chatbot** to see articles appearing in the news sidebar
4. **Customize the workflow** based on your specific news sources

## 📞 **Support**

If you need help with the integration, check:
- API logs in the chatbot console
- Database queries to verify data storage
- n8n workflow execution logs

The webhook endpoint is now ready to receive your n8n news articles! 🎉

