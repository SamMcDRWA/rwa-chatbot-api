# 🤖 RWA Adele - Tableau Content Assistant

RWA Adele is a professional, customer-facing chatbot that helps users find Tableau workbooks, views, and datasources. It's designed to serve as a landing page for your customers to easily discover and access Tableau content.

## ✨ Features

- **Clean, Professional Interface**: Modern chatbot design perfect for customer-facing use
- **Intelligent Search**: Find Tableau content using natural language queries
- **Sidebar Navigation**: Browse all available workbooks, views, and datasources
- **Favorites System**: Star frequently used content for quick access
- **Real-time Status**: Shows API connection status
- **Quick Actions**: One-click access to common searches

## 🚀 Quick Start

### Option 1: Easy Startup (Recommended)
```bash
python start_rwa_adele.py
```

### Option 2: Manual Startup
1. **Start the API Server:**
   ```bash
   python simple_api.py
   ```

2. **Start the UI (in a new terminal):**
   ```bash
   streamlit run rwa_adele_ui.py
   ```

3. **Open your browser:**
   - RWA Adele UI: http://localhost:8501
   - API Documentation: http://localhost:8000/docs

## 📋 Prerequisites

1. **Database Setup**: Make sure your database is set up and indexed
   ```bash
   python setup_database.py
   python index_site.py
   ```

2. **Environment Variables**: Ensure your `.env` file is configured with:
   - Tableau credentials
   - Database connection
   - OpenAI API key (if using advanced features)

## 🎯 How to Use

### For Customers:
1. **Ask Questions**: Type natural language queries like:
   - "Where can I find sales data?"
   - "Show me all dashboards"
   - "Find workbooks about finance"

2. **Browse Content**: Use the sidebar to explore all available content

3. **Add Favorites**: Click the ⭐ next to any item to add it to your favorites

4. **Quick Actions**: Use the quick action buttons for common searches

### For Administrators:
1. **Update Content**: When new Tableau content is added, run:
   ```bash
   python index_site.py
   ```

2. **Monitor Status**: Check the API status indicator in the sidebar

3. **Customize**: Modify the UI by editing `rwa_adele_ui.py`

## 🔧 Customization

### Changing the Branding:
- Edit the header in `rwa_adele_ui.py` (line ~50)
- Update the title, colors, and styling in the CSS section

### Adding New Quick Actions:
- Modify the quick action buttons section (line ~300)
- Add new buttons with custom search queries

### Modifying Search Behavior:
- Edit `src/search/simple_search.py` for search logic
- Update `simple_api.py` for API endpoints

## 📊 Content Management

### Adding Descriptions to Tableau Content:
1. **In Tableau Server**: Add detailed descriptions to workbooks, views, and datasources
2. **Re-index**: Run `python index_site.py` to pick up new descriptions
3. **Test**: Search for the content to verify descriptions are working

### Best Practices for Descriptions:
- Include what the content shows
- Mention key metrics and time periods
- Add relevant keywords
- Keep it concise but informative

## 🐛 Troubleshooting

### API Not Starting:
- Check if port 8000 is available
- Verify database connection in `.env`
- Run `python setup_database.py` to ensure database is set up

### No Search Results:
- Run `python index_site.py` to ensure content is indexed
- Check if Tableau credentials are correct
- Verify database has data: `SELECT COUNT(*) FROM chatbot.objects;`

### UI Not Loading:
- Check if port 8501 is available
- Verify Streamlit is installed: `pip install streamlit`
- Check the terminal for error messages

## 📁 File Structure

```
├── rwa_adele_ui.py          # Main Streamlit interface
├── simple_api.py            # FastAPI server
├── start_rwa_adele.py       # Easy startup script
├── src/
│   └── search/
│       └── simple_search.py # Search functionality
├── .env                     # Configuration
└── RWA_ADELE_README.md      # This file
```

## 🎨 Interface Design

The interface is designed to be:
- **Customer-friendly**: Clean, professional appearance
- **Mobile-responsive**: Works on all device sizes
- **Accessible**: Clear navigation and status indicators
- **Fast**: Quick search and response times

## 🔒 Security Notes

- The API runs on localhost by default
- For production use, configure proper authentication
- Consider using HTTPS for external access
- Regularly update dependencies

## 📞 Support

For issues or questions:
1. Check the terminal output for error messages
2. Verify all prerequisites are met
3. Test database connectivity
4. Check Tableau API credentials

---

**RWA Adele** - Your intelligent Tableau content assistant! 🤖✨
