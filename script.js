document.addEventListener('DOMContentLoaded', () => {
  const yearEl = document.getElementById('year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  const hero = document.querySelector('.hero');
  const menuButton = document.querySelector('.menu-button');
  const siteNav = document.getElementById('site-navigation');
  const closeMenu = () => {
    document.body.classList.remove('nav-open');
    if (menuButton) {
      menuButton.setAttribute('aria-expanded', 'false');
    }
  };
  if (menuButton && siteNav) {
    const toggleMenu = () => {
      const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
      if (isOpen) {
        closeMenu();
      } else {
        document.body.classList.add('nav-open');
        menuButton.setAttribute('aria-expanded', 'true');
      }
    };
    menuButton.addEventListener('click', toggleMenu);
    siteNav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeMenu);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeMenu();
      }
    });
    const desktopMq = window.matchMedia('(min-width: 768px)');
    const handleMq = (event) => {
      if (event.matches) {
        closeMenu();
      }
    };
    if (desktopMq.addEventListener) {
      desktopMq.addEventListener('change', handleMq);
    } else if (desktopMq.addListener) {
      desktopMq.addListener(handleMq);
    }
  }

  const heroVideo = document.getElementById('hero-video');
  if (hero && heroVideo) {
    const attemptPlay = heroVideo.play();
    if (attemptPlay !== undefined) {
      attemptPlay.catch(() => {
        hero.classList.add('hero-fallback');
        heroVideo.remove();
      });
    }
  } else if (hero) {
    hero.classList.add('hero-fallback');
  }

  const carousel = document.querySelector('.carousel');
  const track = document.querySelector('.carousel-track');
  const slides = track ? Array.from(track.children) : [];
  const prevBtn = document.querySelector('.carousel-btn.prev');
  const nextBtn = document.querySelector('.carousel-btn.next');
  const intervalTime = 6000;
  let currentIndex = 0;
  let autoTimer;

  const updateSlides = () => {
    slides.forEach((slide, index) => {
      slide.setAttribute('aria-hidden', index === currentIndex ? 'false' : 'true');
      slide.setAttribute('tabindex', index === currentIndex ? '0' : '-1');
      slide.setAttribute('aria-label', `Testimonio ${index + 1} de ${slides.length}`);
    });
    if (track) {
      track.style.transform = `translateX(-${currentIndex * 100}%)`;
    }
  };

  const goTo = (index) => {
    if (!slides.length) return;
    currentIndex = (index + slides.length) % slides.length;
    updateSlides();
  };

  const next = () => goTo(currentIndex + 1);
  const prev = () => goTo(currentIndex - 1);

  const startAuto = () => {
    if (autoTimer || !slides.length) return;
    autoTimer = window.setInterval(next, intervalTime);
  };

  const stopAuto = () => {
    if (autoTimer) {
      window.clearInterval(autoTimer);
      autoTimer = undefined;
    }
  };

  if (slides.length) {
    updateSlides();
    startAuto();

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        stopAuto();
        next();
        startAuto();
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        stopAuto();
        prev();
        startAuto();
      });
    }

    if (carousel) {
      const pauseEvents = ['mouseenter', 'focusin', 'touchstart'];
      const resumeEvents = ['mouseleave', 'touchend'];

      pauseEvents.forEach((event) => {
        carousel.addEventListener(event, stopAuto);
      });
      resumeEvents.forEach((event) => {
        carousel.addEventListener(event, startAuto);
      });
      carousel.addEventListener('focusout', () => {
        if (!carousel.contains(document.activeElement)) {
          startAuto();
        }
      });
    }
  }

  const contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', (event) => {
      const honeypot = contactForm.querySelector('input[name="empresa"]');
      if (honeypot && honeypot.value.trim()) {
        event.preventDefault();
      }
    });
  }
});
