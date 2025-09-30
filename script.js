// RWA Adele Frontend JavaScript
console.log('Script.js loading...');
console.log('DOM loaded, initializing chatbot...');

class RWAChatbot {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000';
        this.messages = [];
        this.conversationHistory = [];
        this.favorites = [];
        this.workbooks = [];
        this.projects = [];
        this.news = [];
        this.apiOnline = false;
        
        this.init();
    }

    init() {
        console.log('RWAChatbot initializing...');
        this.setupEventListeners();
        this.checkApiStatus();
        this.loadFavorites(); // Load favorites first
        this.loadProjects();
        this.loadNews();
        this.setupNewsToggle();
        this.setupNewsResize();
        console.log('RWAChatbot initialization complete');
    }

    setupEventListeners() {
        console.log('Setting up event listeners...');
        
        // Chat form submission
        document.getElementById('chatForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Quick action buttons
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                this.handleQuickAction(action);
            });
        });

        // Filter change - removed since filterType element was removed from HTML

        // Enter key in input
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Sidebar resize functionality
        this.setupSidebarResize();
    }

    async checkApiStatus() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(`${this.apiBaseUrl}/health`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            this.apiOnline = response.ok;
            this.updateApiStatus();
        } catch (error) {
            console.log('API connection error:', error);
            this.apiOnline = false;
            this.updateApiStatus();
        }
    }

    updateApiStatus() {
        const statusDot = document.getElementById('apiStatus');
        const statusText = document.getElementById('apiStatusText');
        
        if (this.apiOnline) {
            statusDot.classList.add('online');
            statusText.textContent = 'API Online';
        } else {
            statusDot.classList.remove('online');
            statusText.textContent = 'API Offline';
        }
    }

    async loadProjects() {
        try {
            console.log('Loading projects from:', `${this.apiBaseUrl}/projects`);
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch(`${this.apiBaseUrl}/projects`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            console.log('Projects response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                this.projects = data.projects || [];
                console.log('Loaded projects:', this.projects.length);
                console.log('Projects data:', this.projects);
                this.renderProjects();
            } else {
                console.error('Projects API error:', response.status, response.statusText);
                this.showProjectsError();
            }
        } catch (error) {
            console.error('Error loading projects:', error);
            this.showProjectsError();
        }
    }

    renderProjects() {
        const container = document.getElementById('projectsList');
        if (this.projects.length === 0) {
            container.innerHTML = '<p class="empty-state">No projects found</p>';
            return;
        }

        console.log('Rendering projects:', this.projects.length);

        // Clear container first
        container.innerHTML = '';

        // Create projects using DOM methods instead of template literals
        this.projects.forEach((project, index) => {
            const projectItem = document.createElement('div');
            projectItem.className = 'project-item';
            projectItem.setAttribute('data-project', project.project_name);
            projectItem.setAttribute('data-index', index);

            // Project header
            const projectHeader = document.createElement('div');
            projectHeader.className = 'project-header';
            projectHeader.setAttribute('data-project-index', index);

            const folderIcon = document.createElement('i');
            folderIcon.className = 'fas fa-folder';

            const projectName = document.createElement('span');
            projectName.className = 'project-name';
            projectName.textContent = project.project_name || 'Unknown Project';
            
            // Debug logging
            console.log(`Setting project name for index ${index}: "${project.project_name}"`);

            const expandIcon = document.createElement('i');
            expandIcon.className = 'fas fa-chevron-down expand-icon';
            expandIcon.setAttribute('data-icon-index', index);

            projectHeader.appendChild(folderIcon);
            projectHeader.appendChild(projectName);
            projectHeader.appendChild(expandIcon);

            // Workbooks dropdown
            const workbooksDropdown = document.createElement('div');
            workbooksDropdown.className = 'workbooks-dropdown';
            workbooksDropdown.setAttribute('data-dropdown-index', index);

            console.log(`Project ${index}: ${project.project_name} has ${project.workbooks.length} workbooks`);
            
            project.workbooks.forEach((workbook, wbIndex) => {
                console.log(`  Creating workbook: ${workbook.title}`);
                
                const workbookItem = document.createElement('div');
                workbookItem.className = 'workbook-item';
                workbookItem.setAttribute('data-workbook-index', `${index}-${wbIndex}`);
                workbookItem.setAttribute('data-url', workbook.url);

                const workbookTitle = document.createElement('div');
                workbookTitle.className = 'workbook-title';
                workbookTitle.textContent = workbook.title;

                const favoriteBtn = document.createElement('button');
                favoriteBtn.className = 'favorite-btn';
                favoriteBtn.setAttribute('data-favorite-index', `${index}-${wbIndex}`);
                favoriteBtn.setAttribute('data-title', workbook.title);
                favoriteBtn.setAttribute('data-url', workbook.url);
                favoriteBtn.setAttribute('data-project-index', index);
                favoriteBtn.setAttribute('data-workbook-index', wbIndex);

                // Check if this workbook is already favorited
                const isFavorited = this.favorites.some(f => f.title === workbook.title && f.url === workbook.url);
                if (isFavorited) {
                    favoriteBtn.classList.add('favorited');
                }

                const starIcon = document.createElement('i');
                starIcon.className = 'fas fa-star';
                favoriteBtn.appendChild(starIcon);

                // Add direct click listener to this specific button
                favoriteBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Direct favorite button click!', { title: workbook.title, url: workbook.url, projectIndex: index, workbookIndex: wbIndex });
                    this.toggleFavorite(workbook.title, workbook.url, index, wbIndex);
                });

                workbookItem.appendChild(workbookTitle);
                workbookItem.appendChild(favoriteBtn);
                workbooksDropdown.appendChild(workbookItem);
            });

            projectItem.appendChild(projectHeader);
            projectItem.appendChild(workbooksDropdown);
            container.appendChild(projectItem);
        });

        // Add event listeners after rendering
        this.attachProjectEventListeners();
        
        // Update star states based on current favorites
        this.updateProjectStarStates();
        
        // Debug: Check DOM after a short delay
        setTimeout(() => {
            const container = document.getElementById('projectsList');
            const favoriteButtons = container.querySelectorAll('.favorite-btn');
            console.log('DEBUG: After render, found favorite buttons:', favoriteButtons.length);
            console.log('DEBUG: Container innerHTML length:', container.innerHTML.length);
        }, 1000);
    }

    attachProjectEventListeners() {
        const container = document.getElementById('projectsList');
        console.log('Attaching project event listeners with delegation...');
        
        // Remove any existing listeners to avoid duplicates
        container.removeEventListener('click', this.handleProjectClick);
        
        // Use event delegation - single listener on container
        this.handleProjectClick = (e) => {
            console.log('Click detected on:', e.target, e.target.className, e.target.tagName);
            
            // Handle project header clicks
            if (e.target.closest('.project-header')) {
                e.preventDefault();
                e.stopPropagation();
                const header = e.target.closest('.project-header');
                const projectIndex = header.dataset.projectIndex;
                console.log('Project header clicked:', projectIndex);
                this.toggleProject(projectIndex);
                return;
            }
            
            // Handle favorite button clicks - now handled by direct listeners
            // This section is kept for any remaining edge cases
            
            // Handle workbook item clicks (but not favorite buttons)
            if (e.target.closest('.workbook-item') && !e.target.classList.contains('favorite-btn')) {
                const item = e.target.closest('.workbook-item');
                const url = item.dataset.url;
                console.log('Workbook item clicked:', url);
                this.openWorkbook(url);
                return;
            }
        };
        
        container.addEventListener('click', this.handleProjectClick);
        console.log('Event delegation attached to projects container');
    }

    toggleProject(projectIndex) {
        const projectItem = document.querySelector(`[data-project-index="${projectIndex}"]`).parentElement;
        const dropdown = projectItem.querySelector(`[data-dropdown-index="${projectIndex}"]`);
        const icon = projectItem.querySelector(`[data-icon-index="${projectIndex}"]`);
        
        console.log(`Toggling project ${projectIndex}:`, projectItem, dropdown, icon);
        
        if (dropdown && icon) {
            if (projectItem.classList.contains('expanded')) {
                projectItem.classList.remove('expanded');
                dropdown.style.maxHeight = '0';
                icon.style.transform = 'rotate(0deg)';
                console.log(`Collapsed project ${projectIndex}`);
            } else {
                projectItem.classList.add('expanded');
                dropdown.style.maxHeight = dropdown.scrollHeight + 'px';
                icon.style.transform = 'rotate(180deg)';
                console.log(`Expanded project ${projectIndex}`);
            }
        }
    }

    openWorkbook(url) {
        if (url) {
            window.open(url, '_blank');
        }
    }

    showProjectsError() {
        const container = document.getElementById('projectsList');
        container.innerHTML = '<p class="empty-state">Error loading projects. Please check API connection.</p>';
    }


    openWorkbook(url) {
        if (url) {
            window.open(url, '_blank');
        }
    }

    selectWorkbook(workbookId) {
        const workbook = this.workbooks.find(w => w.id === workbookId);
        if (workbook) {
            this.addMessage('user', `Show me details about ${workbook.title}`);
            this.searchContent(`Show me details about ${workbook.title}`);
        }
    }

    toggleFavorite(title, url, projectIndex, workbookIndex) {
        console.log('toggleFavorite called with:', { title, url, projectIndex, workbookIndex });
        console.log('Current projects:', this.projects.length);
        console.log('Current favorites:', this.favorites.length);
        
        // Find the workbook in the projects data
        const workbook = this.projects[projectIndex]?.workbooks[workbookIndex];
        console.log('Found workbook:', workbook);
        
        if (!workbook) {
            console.error('Workbook not found at projectIndex:', projectIndex, 'workbookIndex:', workbookIndex);
            return;
        }

        const isFavorited = this.favorites.some(f => f.title === title && f.url === url);
        console.log('Is favorited:', isFavorited);
        
        const btn = document.querySelector(`[data-favorite-index="${projectIndex}-${workbookIndex}"]`);
        console.log('Found button:', btn);
        
        if (isFavorited) {
            // Remove from favorites
            this.favorites = this.favorites.filter(f => !(f.title === title && f.url === url));
            if (btn) btn.classList.remove('favorited');
            console.log(`Removed "${title}" from favorites`);
        } else {
            // Add to favorites
            this.favorites.push({
                id: workbook.id,
                title: workbook.title,
                url: workbook.url,
                description: workbook.description,
                project_name: this.projects[projectIndex].project_name
            });
            if (btn) btn.classList.add('favorited');
            console.log(`Added "${title}" to favorites`);
        }

        this.saveFavorites();
        this.renderFavorites();
    }

    renderFavorites() {
        const container = document.getElementById('favoritesList');
        if (this.favorites.length === 0) {
            container.innerHTML = '<p class="empty-state">No favorites yet. Click the star on any workbook to add it here!</p>';
            return;
        }

        container.innerHTML = this.favorites.map(workbook => `
            <div class="workbook-item" data-url="${workbook.url}">
                <div>
                    <div class="workbook-title">${workbook.title}</div>
                    <div class="workbook-type">${workbook.project_name}</div>
                </div>
                <button class="favorite-btn favorited" data-title="${workbook.title}" data-url="${workbook.url}">
                    <i class="fas fa-star"></i>
                </button>
            </div>
        `).join('');

        // Add event listeners
        container.querySelectorAll('.workbook-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('favorite-btn')) {
                    const url = item.dataset.url;
                    this.openWorkbook(url);
                }
            });
        });

        container.querySelectorAll('.favorite-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const title = btn.dataset.title;
                const url = btn.dataset.url;
                // Remove from favorites when clicked in favorites list
                this.favorites = this.favorites.filter(f => !(f.title === title && f.url === url));
                this.saveFavorites();
                this.renderFavorites();
                this.updateProjectStarStates(); // Update star states in projects section
                console.log(`Removed "${title}" from favorites`);
            });
        });
    }

    updateProjectStarStates() {
        // Update star states in the projects section based on current favorites
        const projectButtons = document.querySelectorAll('#projectsList .favorite-btn');
        projectButtons.forEach(btn => {
            const title = btn.dataset.title;
            const url = btn.dataset.url;
            const isFavorited = this.favorites.some(f => f.title === title && f.url === url);
            
            if (isFavorited) {
                btn.classList.add('favorited');
            } else {
                btn.classList.remove('favorited');
            }
        });
    }

    loadFavorites() {
        const saved = localStorage.getItem('rwa-favorites');
        if (saved) {
            this.favorites = JSON.parse(saved);
            this.renderFavorites();
            // Update star states in projects section if it's already rendered
            if (document.querySelectorAll('#projectsList .favorite-btn').length > 0) {
                this.updateProjectStarStates();
            }
        }
    }

    saveFavorites() {
        localStorage.setItem('rwa-favorites', JSON.stringify(this.favorites));
    }

    filterWorkbooks(type) {
        // This would filter workbooks by type
        // For now, just re-render all workbooks
        this.renderWorkbooks();
    }

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message) return;

        // Add user message
        this.addMessage('user', message);
        input.value = '';

        // Show loading state
        this.showTypingIndicator();

        // Search for content
        await this.searchContent(message);
    }

    async searchContent(query) {
        try {
            console.log('Searching for:', query);
            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                mode: 'cors',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: query,
                    conversation_history: this.getConversationHistory()
                })
            });

            console.log('Response status:', response.status);
            
            if (response.ok) {
                const results = await response.json();
                console.log('Chat results:', results);
                this.handleChatResults(results);
            } else {
                console.error('API error:', response.status, response.statusText);
                this.addMessage('assistant', 'Sorry, I encountered an error while searching. Please try again.');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.addMessage('assistant', 'Sorry, I couldn\'t connect to the search service. Please check if the API is running.');
        }

        this.hideTypingIndicator();
    }

    getConversationHistory() {
        // Return the last 10 messages for context
        return this.conversationHistory.slice(-10);
    }

    handleChatResults(response) {
        // Use the response from the chat API
        const message = response.response || "I couldn't find any Tableau content matching your query. Try rephrasing your question or check the sidebar for available content.";
        this.addMessage('assistant', message);
        
        // Store conversation history from the API
        if (response.conversation_history) {
            this.conversationHistory = response.conversation_history;
        }
        
        // Ensure scroll to bottom after assistant responds
        this.scrollToBottom();
    }

    addMessage(role, content) {
        this.messages.push({ role, content });
        this.renderMessages();
    }

    renderMessages() {
        const container = document.getElementById('messagesContainer');
        const welcomeMessage = document.getElementById('welcomeMessage');
        
        if (this.messages.length === 0) {
            welcomeMessage.style.display = 'flex';
            container.classList.remove('show');
            return;
        }

        welcomeMessage.style.display = 'none';
        container.classList.add('show');
        
        container.innerHTML = this.messages.map(message => `
            <div class="message ${message.role}-message">
                <div class="message-avatar ${message.role}-avatar">
                    ${message.role === 'user' ? 'U' : 'A'}
                </div>
                <div class="message-content">
                    <div class="message-header">
                        ${message.role === 'user' ? 'You' : 'RWA Adele'}
                    </div>
                    <div class="message-text">${this.formatMessage(message.content)}</div>
                </div>
            </div>
        `).join('');

        // Scroll to bottom after DOM update
        this.scrollToBottom();
    }

    scrollToBottom() {
        const chatContainer = document.getElementById('chatContainer');
        const messagesContainer = document.getElementById('messagesContainer');
        
        // Multiple attempts to ensure scrolling works
        const scrollToBottomNow = () => {
            // Method 1: Direct scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Method 2: Scroll last message into view
            const messages = messagesContainer.querySelectorAll('.message');
            if (messages.length > 0) {
                const lastMessage = messages[messages.length - 1];
                lastMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        };
        
        // Try immediately
        scrollToBottomNow();
        
        // Try again after a short delay to ensure DOM is updated
        setTimeout(scrollToBottomNow, 50);
        
        // Try one more time after a longer delay
        setTimeout(scrollToBottomNow, 200);
    }

    setupSidebarResize() {
        const sidebar = document.getElementById('sidebar');
        const resizeHandle = document.getElementById('resizeHandle');
        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        // Load saved width from localStorage
        const savedWidth = localStorage.getItem('sidebarWidth');
        if (savedWidth) {
            sidebar.style.width = savedWidth + 'px';
        }

        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = parseInt(window.getComputedStyle(sidebar).width, 10);
            
            // Add visual feedback
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            
            // Prevent text selection during resize
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const newWidth = startWidth + (e.clientX - startX);
            const minWidth = 200;
            const maxWidth = 600;
            
            // Constrain width within bounds
            const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
            
            sidebar.style.width = constrainedWidth + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                
                // Save the new width to localStorage
                const newWidth = parseInt(window.getComputedStyle(sidebar).width, 10);
                localStorage.setItem('sidebarWidth', newWidth);
            }
        });

        // Handle double-click to reset to default width
        resizeHandle.addEventListener('dblclick', () => {
            sidebar.style.width = '300px';
            localStorage.setItem('sidebarWidth', '300');
        });

        // Prevent text selection on the resize handle
        resizeHandle.addEventListener('selectstart', (e) => {
            e.preventDefault();
        });

        // Touch support for mobile devices
        resizeHandle.addEventListener('touchstart', (e) => {
            e.preventDefault();
            isResizing = true;
            startX = e.touches[0].clientX;
            startWidth = parseInt(window.getComputedStyle(sidebar).width, 10);
        });

        document.addEventListener('touchmove', (e) => {
            if (!isResizing) return;
            e.preventDefault();
            
            const newWidth = startWidth + (e.touches[0].clientX - startX);
            const minWidth = 200;
            const maxWidth = 600;
            
            const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
            sidebar.style.width = constrainedWidth + 'px';
        });

        document.addEventListener('touchend', () => {
            if (isResizing) {
                isResizing = false;
                const newWidth = parseInt(window.getComputedStyle(sidebar).width, 10);
                localStorage.setItem('sidebarWidth', newWidth);
            }
        });

        // Handle window resize to maintain proportions
        window.addEventListener('resize', () => {
            const currentWidth = parseInt(window.getComputedStyle(sidebar).width, 10);
            const maxWidth = Math.min(600, window.innerWidth * 0.5); // Max 50% of screen width
            const minWidth = 200;
            
            if (currentWidth > maxWidth) {
                sidebar.style.width = maxWidth + 'px';
                localStorage.setItem('sidebarWidth', maxWidth);
            } else if (currentWidth < minWidth) {
                sidebar.style.width = minWidth + 'px';
                localStorage.setItem('sidebarWidth', minWidth);
            }
        });
    }

    formatMessage(content) {
        // Convert markdown-like formatting to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        const container = document.getElementById('messagesContainer');
        const welcomeMessage = document.getElementById('welcomeMessage');
        
        welcomeMessage.style.display = 'none';
        container.classList.add('show');
        
        container.innerHTML += `
            <div class="message assistant-message typing-message">
                <div class="message-avatar assistant-avatar">A</div>
                <div class="message-content">
                    <div class="message-header">RWA Adele</div>
                    <div class="message-text">
                        <span class="loading-spinner"></span> Thinking...
                    </div>
                </div>
            </div>
        `;
        
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingMessage = document.querySelector('.typing-message');
        if (typingMessage) {
            typingMessage.remove();
        }
        this.scrollToBottom();
    }

    handleQuickAction(action) {
        switch (action) {
            case 'dashboards':
                this.addMessage('user', 'Show me all dashboards');
                this.searchContent('Show me all dashboards');
                break;
            case 'sales':
                this.addMessage('user', 'Find sales data');
                this.searchContent('Find sales data');
                break;
            case 'clear':
                this.clearChat();
                break;
        }
    }

    clearChat() {
        this.messages = [];
        this.renderMessages();
    }

    async loadNews() {
        try {
            console.log('Loading news from:', `${this.apiBaseUrl}/news`);
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch(`${this.apiBaseUrl}/news`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            console.log('News response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                this.news = data.news || [];
                console.log('Loaded news:', this.news.length);
                this.renderNews();
            } else {
                console.error('News API error:', response.status, response.statusText);
                this.showNewsError();
            }
        } catch (error) {
            console.error('Error loading news:', error);
            this.showNewsError();
        }
    }

    renderNews() {
        const container = document.getElementById('newsContent');
        if (this.news.length === 0) {
            container.innerHTML = '<div class="news-empty"><i class="fas fa-newspaper"></i><p>No news available</p></div>';
            return;
        }

        console.log('Rendering news:', this.news.length);
        container.innerHTML = '';

        this.news.forEach(article => {
            const newsItem = document.createElement('div');
            newsItem.className = 'news-item';
            newsItem.setAttribute('data-url', article.url);
            
            const publishedDate = new Date(article.published_date);
            const formattedDate = publishedDate.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: 'short',
                year: 'numeric'
            });
            
            newsItem.innerHTML = `
                <h4>${article.title}</h4>
                <p>${article.summary}</p>
                <div class="news-meta">
                    <span class="news-source">${article.source}</span>
                    <span class="news-date">${formattedDate}</span>
                </div>
                <div class="news-category">${article.category}</div>
            `;
            
            newsItem.addEventListener('click', () => {
                window.open(article.url, '_blank');
            });
            
            container.appendChild(newsItem);
        });
    }

    showNewsError() {
        const container = document.getElementById('newsContent');
        container.innerHTML = '<div class="news-empty"><i class="fas fa-exclamation-triangle"></i><p>Failed to load news</p></div>';
    }

    setupNewsToggle() {
        const toggle = document.getElementById('newsToggle');
        const sidebar = document.getElementById('newsSidebar');
        
        if (toggle && sidebar) {
            toggle.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
                const icon = toggle.querySelector('i');
                if (sidebar.classList.contains('collapsed')) {
                    icon.className = 'fas fa-chevron-left';
                } else {
                    icon.className = 'fas fa-chevron-right';
                }
            });
        }
    }

    setupNewsResize() {
        const newsSidebar = document.getElementById('newsSidebar');
        const newsResizeHandle = document.getElementById('newsResizeHandle');
        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        // Load saved width from localStorage
        const savedWidth = localStorage.getItem('newsSidebarWidth');
        if (savedWidth) {
            newsSidebar.style.width = savedWidth + 'px';
        }

        newsResizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = parseInt(window.getComputedStyle(newsSidebar).width, 10);
            
            // Add visual feedback
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            
            // Prevent text selection during resize
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const newWidth = startWidth - (e.clientX - startX); // Negative because we're resizing from the right
            const minWidth = 250;
            const maxWidth = 500;
            
            // Constrain width within bounds
            const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
            
            newsSidebar.style.width = constrainedWidth + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                
                // Save the new width to localStorage
                const newWidth = parseInt(window.getComputedStyle(newsSidebar).width, 10);
                localStorage.setItem('newsSidebarWidth', newWidth);
            }
        });

        // Handle double-click to reset to default width
        newsResizeHandle.addEventListener('dblclick', () => {
            newsSidebar.style.width = '300px';
            localStorage.setItem('newsSidebarWidth', '300');
        });

        // Prevent text selection on the resize handle
        newsResizeHandle.addEventListener('selectstart', (e) => {
            e.preventDefault();
        });

        // Touch support for mobile devices
        newsResizeHandle.addEventListener('touchstart', (e) => {
            e.preventDefault();
            isResizing = true;
            startX = e.touches[0].clientX;
            startWidth = parseInt(window.getComputedStyle(newsSidebar).width, 10);
        });

        document.addEventListener('touchmove', (e) => {
            if (!isResizing) return;
            e.preventDefault();
            
            const newWidth = startWidth - (e.touches[0].clientX - startX); // Negative because we're resizing from the right
            const minWidth = 250;
            const maxWidth = 500;
            
            const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
            newsSidebar.style.width = constrainedWidth + 'px';
        });

        document.addEventListener('touchend', () => {
            if (isResizing) {
                isResizing = false;
                const newWidth = parseInt(window.getComputedStyle(newsSidebar).width, 10);
                localStorage.setItem('newsSidebarWidth', newWidth);
            }
        });

        // Handle window resize to maintain proportions
        window.addEventListener('resize', () => {
            const currentWidth = parseInt(window.getComputedStyle(newsSidebar).width, 10);
            const maxWidth = Math.min(500, window.innerWidth * 0.4); // Max 40% of screen width
            const minWidth = 250;
            
            if (currentWidth > maxWidth) {
                newsSidebar.style.width = maxWidth + 'px';
                localStorage.setItem('newsSidebarWidth', maxWidth);
            } else if (currentWidth < minWidth) {
                newsSidebar.style.width = minWidth + 'px';
                localStorage.setItem('newsSidebarWidth', minWidth);
            }
        });
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.rwaChatbot = new RWAChatbot();
});

// Global functions removed - now using class methods

// Removed visibility change handler to prevent loops
