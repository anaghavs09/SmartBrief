// SmartBrief - Connected to Google Sheets
const BACKEND_URL = 'https://script.google.com/macros/s/AKfycbzVOQldUHHDhvtA0wk_6ZPF85I-e6OxfwObHPbjVhyNQzTIaulYT0BLwmcMEpErh-ueGQ/exec';

const form = document.getElementById('subscribeForm');
const emailInput = document.getElementById('emailInput');
const subscribeBtn = document.getElementById('subscribeBtn');
const messageDiv = document.getElementById('message');
const locationInfo = document.getElementById('locationInfo');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = emailInput.value.trim();
    
    if (!email) {
        showMessage('Please enter your email address', 'error');
        return;
    }
    
    subscribeBtn.disabled = true;
    subscribeBtn.textContent = 'Getting Location...';
    
    if (!navigator.geolocation) {
        showMessage('Geolocation is not supported by your browser', 'error');
        subscribeBtn.disabled = false;
        subscribeBtn.textContent = 'Subscribe';
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            
            const locationName = await getLocationName(latitude, longitude);
            
            locationInfo.textContent = `📍 Location detected: ${locationName}`;
            locationInfo.classList.add('show');
            
            subscribeBtn.textContent = 'Subscribing...';
            
            try {
                // Send to Google Apps Script
                await fetch(BACKEND_URL, {
                    method: 'POST',
                    mode: 'no-cors',  // Required for Apps Script
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: email,
                        latitude: latitude,
                        longitude: longitude,
                        location_name: locationName
                    })
                });
                
                // no-cors means we can't read response, assume success
                showMessage('🎉 Subscribed! You\'ll receive your briefing at 7 AM your local time!', 'success');
                emailInput.value = '';
                
            } catch (error) {
                showMessage('❌ Failed to subscribe. Please try again.', 'error');
                console.error('Error:', error);
            }
            
            subscribeBtn.disabled = false;
            subscribeBtn.textContent = 'Subscribe';
        },
        (error) => {
            let errorMessage = 'Unable to get your location. ';
            
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage += 'Please allow location access.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage += 'Location information is unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage += 'Location request timed out.';
                    break;
                default:
                    errorMessage += 'An unknown error occurred.';
            }
            
            showMessage(errorMessage, 'error');
            subscribeBtn.disabled = false;
            subscribeBtn.textContent = 'Subscribe';
        }
    );
});

async function getLocationName(lat, lon) {
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`
        );
        const data = await response.json();
        
        const city = data.address.city || data.address.town || data.address.village || 'Unknown';
        const country = data.address.country || 'Unknown';
        
        return `${city}, ${country}`;
    } catch (error) {
        console.error('Error getting location name:', error);
        return `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
    }
}

function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}