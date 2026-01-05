const BACKEND_URL = 'https://script.google.com/macros/s/AKfycbzVOQldUHHDhvtA0wk_6ZPF85I-e6OxfwObHPbjVhyNQzTIaulYT0BLwmcMEpErh-ueGQ/exec';

// ===== MOBILE MENU =====
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const navLinks = document.getElementById('navLinks');

if (mobileMenuBtn) {
  mobileMenuBtn.addEventListener('click', () => {
    mobileMenuBtn.classList.toggle('active');
    navLinks.classList.toggle('active');
  });

  // Close menu when clicking on a link
  document.querySelectorAll('.nav-link, .nav-link-cta').forEach(link => {
    link.addEventListener('click', () => {
      mobileMenuBtn.classList.remove('active');
      navLinks.classList.remove('active');
    });
  });

  // Close menu when clicking outside
  document.addEventListener('click', (e) => {
    if (!mobileMenuBtn.contains(e.target) && !navLinks.contains(e.target)) {
      mobileMenuBtn.classList.remove('active');
      navLinks.classList.remove('active');
    }
  });
}

// ===== SMOOTH SCROLL =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});

// ===== NAVBAR SCROLL EFFECT =====
const navbar = document.querySelector('.navbar');
let lastScroll = 0;

window.addEventListener('scroll', () => {
  const currentScroll = window.pageYOffset;
  
  if (currentScroll > 100) {
    navbar.style.boxShadow = '0 4px 20px rgba(20, 184, 166, 0.2)';
    navbar.style.background = 'rgba(255, 255, 255, 0.95)';
  } else {
    navbar.style.boxShadow = '0 2px 12px rgba(20, 184, 166, 0.15)';
    navbar.style.background = 'rgba(255, 255, 255, 0.9)';
  }
  
  lastScroll = currentScroll;
});

// ===== SUBSCRIBE FUNCTIONALITY =====
const subscribeForm = document.getElementById('subscribeForm');
const unsubscribeForm = document.getElementById('unsubscribeForm');
const emailInput = document.getElementById('emailInput');
const messageDiv = document.getElementById('message');
const locationInfo = document.getElementById('locationInfo');

if (subscribeForm) {
  subscribeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = emailInput.value.trim();
    
    if (!email || !isValidEmail(email)) {
      showMessage('Please enter a valid email address', 'error');
      return;
    }
    
    if (!navigator.geolocation) {
      showMessage('Geolocation is not supported by your browser', 'error');
      return;
    }
    
    const btn = document.getElementById('subscribeBtn');
    const btnText = btn.querySelector('.btn-text');
    const originalText = btnText.textContent;
    btnText.textContent = 'Processing...';
    btn.disabled = true;
    
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        
        const locationName = await getLocationName(lat, lon);
        
        if (locationInfo) {
          locationInfo.textContent = `📍 Detected location: ${locationName}`;
          locationInfo.style.display = 'block';
        }
        
        try {
          await fetch(BACKEND_URL, {
            method: 'POST',
            mode: 'no-cors',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action: 'subscribe',
              email: email,
              latitude: lat,
              longitude: lon,
              location_name: locationName
            })
          });
          
          showMessage('🎉 Success! You\'ll receive your SmartBrief daily.', 'success');
          emailInput.value = '';
          
          createConfetti();
          
        } catch (error) {
          showMessage('Something went wrong. Please try again.', 'error');
        } finally {
          btnText.textContent = originalText;
          btn.disabled = false;
        }
      },
      (error) => {
        showMessage('Please allow location access to subscribe.', 'error');
        btnText.textContent = originalText;
        btn.disabled = false;
      }
    );
  });
}

// ===== UNSUBSCRIBE FUNCTIONALITY =====
if (unsubscribeForm) {
  unsubscribeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = emailInput.value.trim();
    
    if (!email || !isValidEmail(email)) {
      showMessage('Please enter a valid email address', 'error');
      return;
    }
    
    const btn = document.querySelector('.btn-unsubscribe');
    const btnText = btn.querySelector('.btn-text');
    const originalText = btnText.textContent;
    btnText.textContent = 'Processing...';
    btn.disabled = true;
    
    try {
      await fetch(BACKEND_URL, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'unsubscribe',
          email: email
        })
      });
      
      showMessage('✅ You have been unsubscribed. Sorry to see you go!', 'success');
      emailInput.value = '';
      
    } catch (error) {
      showMessage('Something went wrong. Please try again.', 'error');
    } finally {
      btnText.textContent = originalText;
      btn.disabled = false;
    }
  });
}

// ===== HELPER FUNCTIONS =====
function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

async function getLocationName(lat, lon) {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
      {
        headers: {
          'User-Agent': 'SmartBrief/1.0'
        }
      }
    );
    const data = await response.json();
    
    const city = data.address.city || data.address.town || data.address.village || 'Unknown';
    const country = data.address.country || 'Unknown';
    
    return `${city}, ${country}`;
  } catch (error) {
    console.error('Location fetch error:', error);
    return `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
  }
}

function showMessage(text, type) {
  if (messageDiv) {
    messageDiv.textContent = text;
    messageDiv.className = `message-box ${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
      messageDiv.style.opacity = '0';
      setTimeout(() => {
        messageDiv.style.display = 'none';
        messageDiv.style.opacity = '1';
      }, 300);
    }, 5000);
  }
}

// ===== CONFETTI EFFECT =====
function createConfetti() {
  const colors = ['#14B8A6', '#FF6B6B', '#1E40AF', '#F59E0B', '#6EE7B7'];
  const confettiCount = 50;
  
  for (let i = 0; i < confettiCount; i++) {
    const confetti = document.createElement('div');
    confetti.style.position = 'fixed';
    confetti.style.width = '10px';
    confetti.style.height = '10px';
    confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
    confetti.style.left = Math.random() * 100 + '%';
    confetti.style.top = '-15px';
    confetti.style.opacity = '1';
    confetti.style.transform = 'rotate(' + Math.random() * 360 + 'deg)';
    confetti.style.transition = 'all 3s ease-out';
    confetti.style.pointerEvents = 'none';
    confetti.style.zIndex = '9999';
    confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
    
    document.body.appendChild(confetti);
    
    setTimeout(() => {
      confetti.style.top = '110vh';
      confetti.style.opacity = '0';
      confetti.style.transform = 'rotate(' + (Math.random() * 720 + 360) + 'deg)';
    }, 10);
    
    setTimeout(() => {
      confetti.remove();
    }, 3000);
  }
}

// ===== INTERSECTION OBSERVER FOR SCROLL ANIMATIONS =====
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -80px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, observerOptions);

// ===== PAGE INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
  // Animate elements on scroll
  const animateElements = document.querySelectorAll('.feature-card, .benefit-item');
  animateElements.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
  });
  
  // Auto-fill email from URL parameter
  const urlParams = new URLSearchParams(window.location.search);
  const emailParam = urlParams.get('email');
  
  if (emailParam && emailInput) {
    emailInput.value = decodeURIComponent(emailParam);
    
    if (messageDiv) {
      messageDiv.innerHTML = '📧 Email pre-filled. Click "Unsubscribe" to confirm.';
      messageDiv.className = 'message-box info';
      messageDiv.style.display = 'block';
    }
  }
});

// ===== FEEDBACK BUTTONS =====
const feedbackButtons = document.querySelectorAll('.feedback-btn');
feedbackButtons.forEach(btn => {
  btn.addEventListener('click', function() {
    this.style.opacity = '0.6';
    setTimeout(() => {
      this.style.opacity = '1';
      showMessage('Thank you for your feedback!', 'success');
    }, 150);
  });
});