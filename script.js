const docReady = (fn) => {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fn);
  } else {
    fn();
  }
};

docReady(() => {
  const yearEl = document.getElementById("year");
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  const menuButton = document.querySelector(".menu-button");
  const siteNav = document.getElementById("site-navigation");
  if (menuButton && siteNav) {
    const toggleMenu = () => {
      const expanded = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!expanded));
      siteNav.classList.toggle("open", !expanded);
    };

    menuButton.addEventListener("click", toggleMenu);

    siteNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        menuButton.setAttribute("aria-expanded", "false");
        siteNav.classList.remove("open");
      });
    });
  }

  const video = document.getElementById("hero-video");
  if (video && typeof video.play === "function") {
    const attemptPlay = video.play();
    if (attemptPlay !== undefined) {
      attemptPlay.catch(() => {
        video.parentElement?.classList.add("video-fallback");
        video.remove();
      });
    }
  }

  const form = document.querySelector(".contact-form");
  if (form) {
    form.addEventListener("submit", (event) => {
      const honeypot = form.querySelector("[name='empresa']");
      if (honeypot && honeypot instanceof HTMLInputElement && honeypot.value.trim() !== "") {
        event.preventDefault();
      }
    });
  }

  initCarousel();
});

function initCarousel() {
  const carousel = document.querySelector(".carousel");
  const track = carousel?.querySelector(".carousel-track");
  const slides = track ? Array.from(track.children) : [];
  const prevButton = carousel?.querySelector(".carousel-button.prev");
  const nextButton = carousel?.querySelector(".carousel-button.next");
  const dotsContainer = carousel?.querySelector(".carousel-dots");

  if (!carousel || !track || slides.length === 0 || !prevButton || !nextButton || !dotsContainer) {
    return;
  }

  let currentIndex = 0;
  let autoAdvanceId = null;
  let isPaused = false;

  slides.forEach((_, index) => {
    const dot = document.createElement("button");
    dot.className = "carousel-dot";
    dot.type = "button";
    dot.setAttribute("role", "tab");
    dot.setAttribute("aria-label", `Ir al testimonio ${index + 1}`);
    dot.addEventListener("click", () => {
      goToSlide(index);
      pauseAutoAdvance();
    });
    dotsContainer.appendChild(dot);
  });

  const dots = Array.from(dotsContainer.children);

  const goToSlide = (index) => {
    currentIndex = (index + slides.length) % slides.length;
    const offset = currentIndex * -100;
    track.style.transform = `translateX(${offset}%)`;
    slides.forEach((slide, slideIndex) => {
      slide.setAttribute("aria-hidden", slideIndex !== currentIndex ? "true" : "false");
      slide.tabIndex = slideIndex === currentIndex ? 0 : -1;
    });
    dots.forEach((dot, dotIndex) => {
      dot.setAttribute("aria-selected", dotIndex === currentIndex ? "true" : "false");
    });
  };

  const goToNext = () => {
    goToSlide(currentIndex + 1);
  };

  const goToPrev = () => {
    goToSlide(currentIndex - 1);
  };

  const startAutoAdvance = () => {
    stopAutoAdvance();
    autoAdvanceId = window.setInterval(() => {
      if (!isPaused) {
        goToNext();
      }
    }, 6000);
  };

  const stopAutoAdvance = () => {
    if (autoAdvanceId !== null) {
      window.clearInterval(autoAdvanceId);
      autoAdvanceId = null;
    }
  };

  const pauseAutoAdvance = () => {
    isPaused = true;
    window.setTimeout(() => {
      isPaused = false;
    }, 8000);
  };

  prevButton.addEventListener("click", () => {
    goToPrev();
    pauseAutoAdvance();
  });

  nextButton.addEventListener("click", () => {
    goToNext();
    pauseAutoAdvance();
  });

  carousel.addEventListener("mouseenter", () => {
    isPaused = true;
  });

  carousel.addEventListener("mouseleave", () => {
    isPaused = false;
  });

  carousel.addEventListener("focusin", () => {
    isPaused = true;
  });

  carousel.addEventListener("focusout", () => {
    isPaused = false;
  });

  goToSlide(0);
  startAutoAdvance();
}
