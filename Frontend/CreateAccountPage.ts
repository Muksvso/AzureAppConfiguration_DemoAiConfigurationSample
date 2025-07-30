export class CreateAccountPage {
  private onCreate: (username: string) => void;
  private onBack: () => void;
  private createForm: HTMLFormElement | null = null;
  private usernameInput: HTMLInputElement | null = null;
  private passwordInput: HTMLInputElement | null = null;
  private errorDiv: HTMLElement | null = null;

  constructor(onCreate: (username: string) => void, onBack: () => void) {
    this.onCreate = onCreate;
    this.onBack = onBack;
  }

  public render(): void {
    const app = document.getElementById('app');
    if (!app) return;
    app.innerHTML = `
      <div class="login-container">
        <div class="login-box">
          <img src="./assets/azure-app-configuration-icon.svg" alt="Azure App Configuration Logo" class="login-logo" />
          <h2 class="login-title">Create Account</h2>
          <form id="create-form" class="login-form">
            <input type="text" id="create-username" class="login-input" placeholder="Choose a username" autocomplete="off" required />
            <input type="password" id="create-password" class="login-input" placeholder="Choose a password" autocomplete="off" required style="margin-top:8px;" />
            <button type="submit" class="login-button">Create Account</button>
          </form>
          <button id="back-to-login" class="login-button" style="background: var(--ms-light-gray); color: var(--ms-dark-blue); margin-top: 8px;">Back to Login</button>
          <div id="create-error" class="login-error"></div>
        </div>
      </div>
    `;
    this.bindElements();
    this.bindEvents();
  }

  private bindElements(): void {
    this.createForm = document.getElementById('create-form') as HTMLFormElement;
    this.usernameInput = document.getElementById('create-username') as HTMLInputElement;
    this.passwordInput = document.getElementById('create-password') as HTMLInputElement;
    this.errorDiv = document.getElementById('create-error');
  }

  private bindEvents(): void {
    if (this.createForm) {
      this.createForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleCreate();
      });
    }
    const backBtn = document.getElementById('back-to-login');
    if (backBtn) {
      backBtn.addEventListener('click', () => this.onBack());
    }
  }

  private async handleCreate(): Promise<void> {
    if (!this.usernameInput || !this.passwordInput) return;
    const username = this.usernameInput.value.trim();
    const password = this.passwordInput.value;
    if (!username || !password) {
      if (this.errorDiv) this.errorDiv.textContent = 'Please enter a username and password.';
      return;
    }
    if (this.errorDiv) this.errorDiv.textContent = '';
    try {
      const res = await fetch('/api/create_account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        this.onCreate(username);
      } else {
        if (this.errorDiv) this.errorDiv.textContent = data.error || 'Account creation failed.';
      }
    } catch (err) {
      if (this.errorDiv) this.errorDiv.textContent = 'Network error.';
    }
  }
}
