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

  const storage = {
    get(key) {
      try {
        return window.localStorage.getItem(key);
      } catch (error) {
        return null;
      }
    },
    set(key, value) {
      try {
        window.localStorage.setItem(key, value);
      } catch (error) {
        /* noop */
      }
    },
    remove(key) {
      try {
        window.localStorage.removeItem(key);
      } catch (error) {
        /* noop */
      }
    }
  };

  const DISCOUNT_UNLOCK_KEY = 'petitReveDiscountUnlocked';
  const DISCOUNT_BANNER_DISMISS_KEY = 'petitReveDiscountBannerDismissed';
  const discountBanner = document.getElementById('discount-banner');
  const discountBannerClose = discountBanner ? discountBanner.querySelector('.discount-banner__close') : null;

  const showDiscountBanner = () => {
    if (!discountBanner) return;
    if (storage.get(DISCOUNT_BANNER_DISMISS_KEY) === 'true') return;
    discountBanner.hidden = false;
    window.requestAnimationFrame(() => {
      discountBanner.classList.add('is-visible');
    });
  };

  const hideDiscountBanner = () => {
    if (!discountBanner) return;
    discountBanner.classList.remove('is-visible');
    window.setTimeout(() => {
      discountBanner.hidden = true;
    }, 300);
  };

  if (storage.get(DISCOUNT_UNLOCK_KEY) === 'true') {
    showDiscountBanner();
  }

  if (discountBannerClose) {
    discountBannerClose.addEventListener('click', () => {
      storage.set(DISCOUNT_BANNER_DISMISS_KEY, 'true');
      hideDiscountBanner();
    });
  }

  const miniGame = document.getElementById('mini-game');
  if (miniGame) {
    const miniGameStatus = miniGame.querySelector('#mini-game-status');
    const miniGameChoices = miniGame.querySelectorAll('.mini-game__choice');
    const MIN_GAME_DELAY = 45000;
    const MAX_GAME_DELAY = 90000;
    let miniGameTimer;
    let resultTimer;
    let gameActive = false;
    let lastFocusedElement = null;

    const hasUnlockedDiscount = () => storage.get(DISCOUNT_UNLOCK_KEY) === 'true';

    const resetMiniGame = () => {
      if (miniGameStatus) {
        miniGameStatus.textContent = 'Elegí una estrella y probá tu suerte.';
      }
      miniGameChoices.forEach((choice) => {
        choice.disabled = false;
        choice.classList.remove('is-selected', 'is-winner');
      });
    };

    const clearTimers = () => {
      if (miniGameTimer) {
        window.clearTimeout(miniGameTimer);
        miniGameTimer = undefined;
      }
      if (resultTimer) {
        window.clearTimeout(resultTimer);
        resultTimer = undefined;
      }
    };

    const scheduleMiniGame = () => {
      if (hasUnlockedDiscount() || gameActive) return;
      clearTimers();
      const delay = Math.floor(Math.random() * (MAX_GAME_DELAY - MIN_GAME_DELAY + 1)) + MIN_GAME_DELAY;
      miniGameTimer = window.setTimeout(() => {
        if (document.hidden || gameActive) {
          scheduleMiniGame();
          return;
        }
        openMiniGame();
      }, delay);
    };

    const openMiniGame = () => {
      if (gameActive || hasUnlockedDiscount()) return;
      gameActive = true;
      resetMiniGame();
      lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      miniGame.setAttribute('aria-hidden', 'false');
      miniGame.classList.add('is-visible');
      document.body.classList.add('mini-game-open');
      window.setTimeout(() => {
        if (miniGameChoices[0]) {
          miniGameChoices[0].focus();
        }
      }, 120);
    };

    const closeMiniGame = (options = { shouldReschedule: true }) => {
      if (!gameActive && miniGame.classList.contains('is-visible') === false) return;
      clearTimers();
      miniGame.classList.remove('is-visible');
      miniGame.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('mini-game-open');
      gameActive = false;
      if (lastFocusedElement) {
        lastFocusedElement.focus();
        lastFocusedElement = null;
      }
      if (options.shouldReschedule && !hasUnlockedDiscount()) {
        scheduleMiniGame();
      }
    };

    const handleWin = () => {
      storage.set(DISCOUNT_UNLOCK_KEY, 'true');
      storage.remove(DISCOUNT_BANNER_DISMISS_KEY);
      showDiscountBanner();
      resultTimer = window.setTimeout(() => {
        closeMiniGame({ shouldReschedule: false });
      }, 2600);
    };

    const handleChoiceSelection = (event) => {
      const target = event.currentTarget;
      if (!(target instanceof HTMLButtonElement) || target.disabled) return;
      miniGameChoices.forEach((choice) => {
        choice.disabled = true;
        choice.classList.remove('is-selected', 'is-winner');
      });
      target.classList.add('is-selected');
      const winningIndex = Math.floor(Math.random() * miniGameChoices.length);
      const chosenIndex = Number(target.dataset.choice);
      miniGameChoices.forEach((choice, index) => {
        if (index === winningIndex) {
          choice.classList.add('is-winner');
        }
      });
      if (miniGameStatus) {
        if (chosenIndex === winningIndex) {
          miniGameStatus.textContent = '¡Ganaste! Usá el código SUEÑO5 para obtener 5% OFF.';
          handleWin();
        } else {
          miniGameStatus.textContent = 'Casi, casi... Volveremos a aparecer más tarde.';
          resultTimer = window.setTimeout(() => {
            closeMiniGame();
          }, 2800);
        }
      }
    };

    miniGameChoices.forEach((choice) => {
      choice.addEventListener('click', handleChoiceSelection);
    });

    miniGame.addEventListener('click', (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.dataset.miniGameClose === 'true') {
        closeMiniGame();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && gameActive) {
        closeMiniGame();
      }
    });

    document.addEventListener('visibilitychange', () => {
      if (document.hidden && gameActive) {
        closeMiniGame();
      }
    });

    if (!hasUnlockedDiscount()) {
      scheduleMiniGame();
    }
  }
});
