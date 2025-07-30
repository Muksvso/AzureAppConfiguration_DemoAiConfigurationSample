export class LoginPage {
  private onLogin: (username: string) => void;
  private onCreateAccount: () => void;
  private loginForm: HTMLFormElement | null = null;
  private usernameInput: HTMLInputElement | null = null;
  private passwordInput: HTMLInputElement | null = null;
  private errorDiv: HTMLElement | null = null;

  constructor(onLogin: (username: string) => void, onCreateAccount: () => void) {
    this.onLogin = onLogin;
    this.onCreateAccount = onCreateAccount;
  }

  public render(): void {
    const app = document.getElementById('app');
    if (!app) return;
    app.innerHTML = `
      <div class="login-container">
        <div class="login-box">
          <img src='./assets/azure-app-configuration-icon.svg' alt='Azure App Configuration Logo' class='login-logo' />
          <h2 class='login-title'>Sign in to Chat</h2>
          <form id='login-form' class='login-form'>
            <input type='text' id='username' class='login-input' placeholder='Enter your name' autocomplete='off' required />
            <input type='password' id='password' class='login-input' placeholder='Password' autocomplete='off' required style='margin-top:8px;' />
            <button type='submit' class='login-button'>Login</button>
          </form>
          <button id='create-account-link' class='login-button' style='background: var(--ms-light-gray); color: var(--ms-dark-blue); margin-top: 8px;'>Create Account</button>
          <div id='login-error' class='login-error'></div>
        </div>
      </div>
    `;
    this.bindElements();
    this.bindEvents();
  }

  private bindElements(): void {
    this.loginForm = document.getElementById('login-form') as HTMLFormElement;
    this.usernameInput = document.getElementById('username') as HTMLInputElement;
    this.passwordInput = document.getElementById('password') as HTMLInputElement;
    this.errorDiv = document.getElementById('login-error');
  }

  private bindEvents(): void {
    if (this.loginForm) {
      this.loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleLogin();
      });
    }
    const createAccountBtn = document.getElementById('create-account-link');
    if (createAccountBtn) {
      createAccountBtn.addEventListener('click', () => this.onCreateAccount());
    }
  }

  private async handleLogin(): Promise<void> {
    if (!this.usernameInput || !this.passwordInput) return;
    const username = this.usernameInput.value.trim();
    const password = this.passwordInput.value;
    if (!username || !password) {
      if (this.errorDiv) this.errorDiv.textContent = 'Please enter your name and password.';
      return;
    }
    if (this.errorDiv) this.errorDiv.textContent = '';
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        this.onLogin(username);
      } else {
        if (this.errorDiv) this.errorDiv.textContent = data.error || 'Login failed.';
      }
    } catch (err) {
      if (this.errorDiv) this.errorDiv.textContent = 'Network error.';
    }
  }
}
