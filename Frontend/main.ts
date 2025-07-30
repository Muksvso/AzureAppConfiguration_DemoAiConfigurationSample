
import { App } from './App';
import './CreateAccountPage';
import './LoginPage';
import './styles/main.css';

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.init();
});
