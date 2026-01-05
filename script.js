const BACKEND_URL =
  'https://script.google.com/macros/s/AKfycbzVOQldUHHDhvtA0wk_6ZPF85I-e6OxfwObHPbjVhyNQzTIaulYT0BLwmcMEpErh-ueGQ/exec';

const form = document.getElementById('subscribeForm');
const emailInput = document.getElementById('emailInput');
const subscribeBtn = document.getElementById('subscribeBtn');
const unsubscribeBtn = document.getElementById('unsubscribeBtn');
const messageDiv = document.getElementById('message');
const locationInfo = document.getElementById('locationInfo');

/* 🔀 Mode toggle */
const params = new URLSearchParams(window.location.search);
const mode = params.get('mode');

if (mode === 'unsubscribe') {
  subscribeBtn.style.display = 'none';
  unsubscribeBtn.style.display = 'inline-block';
}

/* ✅ SUBSCRIBE */
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const email = emailInput.value.trim();
  if (!email) return;

  subscribeBtn.disabled = true;
  subscribeBtn.textContent = 'Locating…';

  navigator.geolocation.getCurrentPosition(async (pos) => {
    const lat = pos.coords.latitude;
    const lon = pos.coords.longitude;

    const location = await getLocationName(lat, lon);
    locationInfo.textContent = `📍 ${location}`;

    await fetch(BACKEND_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'subscribe',
        email,
        latitude: lat,
        longitude: lon,
        location_name: location
      })
    });

    messageDiv.textContent = '🎉 Subscribed! Check your inbox at 7 AM.';
    emailInput.value = '';
    subscribeBtn.disabled = false;
    subscribeBtn.textContent = 'Subscribe';
  });
});

/* ❌ UNSUBSCRIBE */
unsubscribeBtn.addEventListener('click', async () => {
  const email = emailInput.value.trim();
  if (!email) {
    messageDiv.textContent = 'Please enter your email.';
    return;
  }

  await fetch(BACKEND_URL, {
    method: 'POST',
    mode: 'no-cors',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'unsubscribe',
      email
    })
  });

  messageDiv.textContent = '✅ You are unsubscribed.';
  emailInput.value = '';
});

/* 🌍 Reverse geocode */
async function getLocationName(lat, lon) {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`
    );
    const data = await res.json();
    return `${data.address.city || 'Unknown'}, ${data.address.country || ''}`;
  } catch {
    return `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
  }
}
