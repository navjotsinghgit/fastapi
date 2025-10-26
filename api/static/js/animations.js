// Background Animation Functions
function createBackgroundAnimations() {
    createFloatingParticles();
    startRealTimeAnimation();
}

function createFloatingParticles() {
    const existingParticles = document.querySelector('.floating-particles');
    if (existingParticles) {
        existingParticles.remove();
    }

    const particleContainer = document.createElement('div');
    particleContainer.className = 'floating-particles';
    document.body.appendChild(particleContainer);

    for (let i = 0; i < 20; i++) {
        createParticle(particleContainer, i);
    }
}

function createParticle(container, index) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    
    particle.style.left = Math.random() * 100 + '%';
    particle.style.animationDelay = Math.random() * 15 + 's';
    particle.style.animationDuration = (15 + Math.random() * 10) + 's';
    
    container.appendChild(particle);
    
    setTimeout(() => {
        if (particle.parentNode) {
            particle.remove();
            createParticle(container, index);
        }
    }, (15 + Math.random() * 10) * 1000);
}

function startRealTimeAnimation() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = (index * 0.1) + 's';
        card.classList.add('card-animate');
    });
    
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        img.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05) rotate(1deg)';
            this.style.filter = 'brightness(1.1) saturate(1.2)';
        });
        
        img.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1) rotate(0deg)';
            this.style.filter = 'brightness(1) saturate(1)';
        });
    });
}

function animateThemeTransition() {
    const body = document.body;
    body.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
    
    const ripple = document.createElement('div');
    ripple.style.cssText = `
        position: fixed; top: 50%; left: 50%; width: 0; height: 0;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        border-radius: 50%; transform: translate(-50%, -50%);
        pointer-events: none; z-index: 9999;
        animation: themeRipple 0.8s ease-out forwards;
    `;
    
    document.body.appendChild(ripple);
    setTimeout(() => ripple.remove(), 800);
}

const animationCSS = `
@keyframes themeRipple {
    0% { width: 0; height: 0; opacity: 0.8; }
    100% { width: 200vmax; height: 200vmax; opacity: 0; }
}
.card-animate { animation: cardFloat 6s ease-in-out infinite; }
@keyframes cardFloat {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-5px); }
}`;

const style = document.createElement('style');
style.textContent = animationCSS;
document.head.appendChild(style);