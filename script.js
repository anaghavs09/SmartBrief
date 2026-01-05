const BACKEND_URL =
  'https://script.google.com/macros/s/AKfycbzVOQldUHHDhvtA0wk_6ZPF85I-e6OxfwObHPbjVhyNQzTIaulYT0BLwmcMEpErh-ueGQ/exec';

const subscribeForm = document.getElementById('subscribeForm');
const unsubscribeForm = document.getElementById('unsubscribeForm');
const emailInput = document.getElementById('emailInput');
const messageDiv = document.getElementById('message');
const locationInfo = document.getElementById('locationInfo');

/* ---------- SUBSCRIBE ---------- */
if (subscribeForm) {
  subscribeForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    if (!email) return;

    navigator.geolocation.getCurrentPosition(async (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;

      await fetch(BACKEND_URL, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'subscribe',
          email,
          latitude: lat,
          longitude: lon
        })
      });

      messageDiv.textContent =
        '🎉 Subscribed! You’ll receive SmartBrief at 7 AM.';
      emailInput.value = '';
    });
  });
}

/* ---------- UNSUBSCRIBE ---------- */
if (unsubscribeForm) {
  unsubscribeForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    if (!email) return;

    await fetch(BACKEND_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'unsubscribe',
        email
      })
    });

    messageDiv.textContent = '✅ You have been unsubscribed.';
    emailInput.value = '';
  });
}
