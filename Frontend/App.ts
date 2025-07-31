import axios from 'axios';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { CreateAccountPage } from './CreateAccountPage';
import { LoginPage } from './LoginPage';
import { ChatMessage, ChatRequest, ChatResponse } from './types';


export class App {
  private chatMessages: HTMLElement | null = null;
  private chatInput: HTMLInputElement | null = null;
  private sendButton: HTMLButtonElement | null = null;
  private chatForm: HTMLFormElement | null = null;
  private messageHistory: ChatMessage[] = [];
  private isWaitingForResponse: boolean = false;
  private username: string | null = null;

  public async init(): Promise<void> {
    this.username = localStorage.getItem('username');
    if (!this.username) {
      this.showLogin();
    } else {
      this.render();
      this.bindElements();
      this.bindEvents();
    }
  }

  private showLogin(): void {
    const loginPage = new LoginPage(
      (username: string) => {
        this.username = username;
        localStorage.setItem('username', username);
        this.render();
        this.bindElements();
        this.bindEvents();
      },
      () => this.showCreateAccount()
    );
    loginPage.render();
  }

  private showCreateAccount(): void {
    const createAccountPage = new CreateAccountPage(
      (username: string) => {
        // Simulate account creation and login
        this.username = username;
        localStorage.setItem('username', username);
        this.render();
        this.bindElements();
        this.bindEvents();
      },
      () => this.showLogin()
    );
    createAccountPage.render();
  }

  private render(): void {
    const app = document.getElementById('app');
    if (!app) return;

    app.innerHTML = `
      <header class="header">
        <div class="header-logo">
          <img src="./assets/azure-app-configuration-icon.svg" alt="Azure App Configuration Logo" />
          <h1 class="header-title">Azure App Configuration AI Chat</h1>
        </div>
        <div class="header-user">
          <span class="user-greeting">Hello, ${this.username ? DOMPurify.sanitize(this.username) : ''}</span>
          <button id="logout-button" class="logout-button">Logout</button>
        </div>
      </header>
      <main class="chat-container">
        <div class="chat-messages" id="chat-messages">
          <div class="welcome-container">
            <img src="./assets/azure-app-configuration-icon.svg" alt="Azure App Configuration Logo" class="welcome-logo" />
            <h2 class="welcome-title">Welcome to Azure App Configuration AI Chat</h2>
            <p class="welcome-description">
              I'm your AI assistant powered by Azure App Configuration. Ask me anything and I'll do my best to help you.
            </p>
          </div>
        </div>
        <div class="chat-input-container">
          <form id="chat-form" class="chat-input-form">
            <input 
              type="text" 
              id="chat-input" 
              class="chat-input" 
              placeholder="Type your message..." 
              autocomplete="off"
            />
            <button type="submit" id="send-button" class="send-button">Send</button>
          </form>
        </div>
      </main>
    `;
  }

  private bindElements(): void {
    this.chatMessages = document.getElementById('chat-messages');
    this.chatInput = document.getElementById('chat-input') as HTMLInputElement;
    this.sendButton = document.getElementById('send-button') as HTMLButtonElement;
    this.chatForm = document.getElementById('chat-form') as HTMLFormElement;
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
      logoutButton.addEventListener('click', () => {
        localStorage.removeItem('username');
        this.username = null;
        this.showLogin();
      });
    }
  }

  private bindEvents(): void {
    if (this.chatForm) {
      this.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleSendMessage();
      });
    }

    if (this.chatInput) {
      this.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });

      // Enable/disable send button based on input
      this.chatInput.addEventListener('input', () => {
        if (this.sendButton) {
          this.sendButton.disabled = !this.chatInput?.value.trim();
        }
      });
    }
  }

  private handleSendMessage(): void {
    if (!this.chatInput || !this.sendButton || this.isWaitingForResponse) return;

    const message = this.chatInput.value.trim();
    if (!message) return;

    // Clear input and disable button
    this.chatInput.value = '';
    this.sendButton.disabled = true;
    this.isWaitingForResponse = true;

    // Add user message to UI
    this.addMessageToUI('user', message);

    // Add user message to history
    this.messageHistory.push({
      role: 'user',
      content: message,
      timestamp: new Date()
    });

    // Show typing indicator
    this.showTypingIndicator();

    // Send message to API
    this.sendMessageToAPI(message);
  }

  private async sendMessageToAPI(message: string): Promise<void> {
    try {
      const request: ChatRequest = {
        message,
        history: this.messageHistory
      };

      const response = await axios.post<ChatResponse>('/api/chat', request);
      // Hide typing indicator
      this.hideTypingIndicator();
      // Update message history with the complete history from response
      this.messageHistory = response.data.history;
      // Add bot message to UI, including agent name
      this.addMessageToUI('bot', response.data.message, response.data.agent_name);
    } catch (error: any) {
      // If unauthorized, redirect to login page
      if (error.response && error.response.status === 401) {
        localStorage.removeItem('username');
        this.username = null;
        this.showLogin();
        return;
      }
      console.error('Error sending message:', error);
      // Hide typing indicator
      this.hideTypingIndicator();
      // Show error message
      this.addMessageToUI('bot', 'Sorry, I encountered an error. Please try again later.');
    } finally {
      this.isWaitingForResponse = false;
      if (this.sendButton) {
        this.sendButton.disabled = false;
      }
      if (this.chatInput) {
        this.chatInput.focus();
      }
    }
  }

  private addMessageToUI(role: 'user' | 'bot', content: string, agentName?: string): void {
    if (!this.chatMessages) return;

    const messageElement = document.createElement('div');
    messageElement.className = `message ${role}`;

    // Format the message content (handle markdown for bot messages)
    let formattedContent = content;
    if (role === 'bot') {
      formattedContent = DOMPurify.sanitize(marked(content));
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let agentHeader = '';
    if (role === 'bot') {
      const displayName = agentName && agentName.trim() ? agentName : 'Agent';
      agentHeader = `<div class="agent-name">${DOMPurify.sanitize(displayName)}</div>`;
    }

    messageElement.innerHTML = `
      ${agentHeader}
      <div class="message-bubble">${role === 'bot' ? formattedContent : content}</div>
      <div class="message-timestamp">${timestamp}</div>
    `;

    this.chatMessages.appendChild(messageElement);
    
    // Scroll to bottom
    this.scrollToBottom();
  }

  private showTypingIndicator(): void {
    if (!this.chatMessages) return;

    const typingIndicator = document.createElement('div');
    typingIndicator.id = 'typing-indicator';
    typingIndicator.className = 'message bot';
    typingIndicator.innerHTML = `
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;

    this.chatMessages.appendChild(typingIndicator);
    this.scrollToBottom();
  }

  private hideTypingIndicator(): void {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
      typingIndicator.remove();
    }
  }

  private scrollToBottom(): void {
    if (this.chatMessages) {
      this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
  }
}