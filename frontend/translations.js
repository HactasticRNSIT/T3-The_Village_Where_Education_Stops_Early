window.changeLanguage = function(lang) {
  // Find the hidden Google Translate dropdown
  const googleSelect = document.querySelector('.goog-te-combo');
  
  if (googleSelect) {
    googleSelect.value = lang;
    // Dispatch a change event so Google Translate knows to update the page
    googleSelect.dispatchEvent(new Event('change'));
  }
};

document.addEventListener('DOMContentLoaded', () => {
  const langSelector = document.getElementById('lang-selector');

  if (langSelector) {
    langSelector.addEventListener('change', (e) => {
      window.changeLanguage(e.target.value);
    });
  }
});
