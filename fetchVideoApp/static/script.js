// Enhanced JavaScript for FetchVideo

// Loading spinner functionality
const spinnerWrapperEl = document.querySelector(".spinner-wrapper");

window.addEventListener("load", () => {
  if (spinnerWrapperEl) {
    spinnerWrapperEl.style.opacity = "0";
    setTimeout(() => {
      spinnerWrapperEl.style.display = "none";
    }, 300);
  }
});

// URL validation function
function isValidYouTubeUrl(url) {
  const youtubeRegex =
    /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/)|youtu\.be\/)/;
  return youtubeRegex.test(url);
}

// Extract video ID from URL
function extractVideoId(url) {
  const match = url.match(
    /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/
  );
  return match ? match[1] : null;
}

// Toast notification system
class ToastManager {
  constructor() {
    this.toasts = new Map();
  }

  show(message, type = "info", duration = 5000) {
    const toastId = Date.now().toString();
    const toastHtml = this.createToastHtml(toastId, message, type);

    // Add to DOM
    document.body.insertAdjacentHTML("beforeend", toastHtml);

    // Initialize Bootstrap toast
    const toastElement = document.getElementById(`toast-${toastId}`);
    const toast = new bootstrap.Toast(toastElement, { delay: duration });

    // Store reference
    this.toasts.set(toastId, { element: toastElement, toast: toast });

    // Show toast
    toast.show();

    // Auto remove from DOM after hiding
    toastElement.addEventListener("hidden.bs.toast", () => {
      toastElement.remove();
      this.toasts.delete(toastId);
    });

    return toastId;
  }

  createToastHtml(id, message, type) {
    const typeClasses = {
      success: "bg-success text-white",
      error: "bg-danger text-white",
      warning: "bg-warning text-dark",
      info: "bg-info text-white",
    };

    const icons = {
      success: "fa-check-circle",
      error: "fa-exclamation-triangle",
      warning: "fa-exclamation-circle",
      info: "fa-info-circle",
    };

    return `
            <div class="toast-container position-fixed bottom-0 end-0 p-3">
                <div id="toast-${id}" class="toast ${
      typeClasses[type]
    }" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header">
                        <i class="fas ${icons[type]} me-2"></i>
                        <strong class="me-auto">${
                          type.charAt(0).toUpperCase() + type.slice(1)
                        }</strong>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                    <div class="toast-body">${message}</div>
                </div>
            </div>
        `;
  }

  hide(toastId) {
    const toastData = this.toasts.get(toastId);
    if (toastData) {
      toastData.toast.hide();
    }
  }

  hideAll() {
    this.toasts.forEach((toastData) => {
      toastData.toast.hide();
    });
  }
}

// Global toast manager instance
const toastManager = new ToastManager();

// Form validation and enhancement
document.addEventListener("DOMContentLoaded", function () {
  // Enhanced form validation for YouTube URLs
  const youtubeForm = document.getElementById("youtubeForm");
  if (youtubeForm) {
    const urlInput = document.getElementById("id_youtube_link");
    const submitBtn = youtubeForm.querySelector('button[type="submit"]');

    if (urlInput && submitBtn) {
      // Real-time validation
      urlInput.addEventListener("input", function () {
        const url = this.value.trim();
        const isValid = isValidYouTubeUrl(url);

        if (url === "") {
          this.classList.remove("is-valid", "is-invalid");
          submitBtn.disabled = false;
        } else if (isValid) {
          this.classList.add("is-valid");
          this.classList.remove("is-invalid");
          submitBtn.disabled = false;
        } else {
          this.classList.add("is-invalid");
          this.classList.remove("is-valid");
          submitBtn.disabled = true;
        }
      });

      // Form submission handler
      youtubeForm.addEventListener("submit", function (e) {
        const url = urlInput.value.trim();

        if (!url) {
          e.preventDefault();
          toastManager.show("Please enter a YouTube URL", "error");
          return;
        }

        if (!isValidYouTubeUrl(url)) {
          e.preventDefault();
          toastManager.show("Please enter a valid YouTube URL", "error");
          return;
        }

        // Show processing state
        submitBtn.innerHTML =
          '<i class="fas fa-spinner fa-spin me-2"></i>Fetching...';
        submitBtn.disabled = true;

        // Show progress toast
        toastManager.show("Fetching video details...", "info", 10000);
      });
    }
  }

  // Download button enhancements
  const downloadButtons = document.querySelectorAll(
    'button[name="video_quality"], a[href*="download"]'
  );
  downloadButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const originalText = this.innerHTML;
      this.innerHTML =
        '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
      this.disabled = true;

      // Show processing toast for video downloads
      if (this.name === "video_quality") {
        toastManager.show("Processing video download...", "info", 15000);
      }

      // Reset button after 30 seconds (fallback)
      setTimeout(() => {
        if (this.innerHTML.includes("Processing")) {
          this.innerHTML = originalText;
          this.disabled = false;
        }
      }, 30000);
    });
  });

  // Copy URL functionality
  const copyButtons = document.querySelectorAll("[data-copy-url]");
  copyButtons.forEach((button) => {
    button.addEventListener("click", async function () {
      const url = this.dataset.copyUrl || this.dataset.url;
      try {
        await navigator.clipboard.writeText(url);
        toastManager.show("URL copied to clipboard!", "success");
      } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement("textarea");
        textArea.value = url;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
        toastManager.show("URL copied to clipboard!", "success");
      }
    });
  });

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });

  // Add loading animation to cards on hover
  const cards = document.querySelectorAll(".card-custom");
  cards.forEach((card) => {
    card.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-5px) scale(1.02)";
    });

    card.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0) scale(1)";
    });
  });

  // Progress bar animation for download progress
  function animateProgressBar(selector, targetWidth, duration = 2000) {
    const progressBar = document.querySelector(selector);
    if (!progressBar) return;

    let currentWidth = 0;
    const increment = targetWidth / (duration / 16); // 60fps

    const animate = () => {
      currentWidth += increment;
      if (currentWidth >= targetWidth) {
        progressBar.style.width = targetWidth + "%";
        return;
      }
      progressBar.style.width = currentWidth + "%";
      requestAnimationFrame(animate);
    };

    animate();
  }

  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", function (e) {
    // Ctrl/Cmd + K to focus search input
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      const searchInput = document.getElementById("id_youtube_link");
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }

    // Escape to clear search
    if (e.key === "Escape") {
      const searchInput = document.getElementById("id_youtube_link");
      if (searchInput && document.activeElement === searchInput) {
        searchInput.value = "";
        searchInput.blur();
      }
    }
  });

  // Lazy loading for images
  const images = document.querySelectorAll("img[data-src]");
  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.classList.remove("lazy");
        observer.unobserve(img);
      }
    });
  });

  images.forEach((img) => imageObserver.observe(img));

  // Add pulse animation to download buttons on page load
  setTimeout(() => {
    const downloadBtns = document.querySelectorAll(
      ".btn-custom, .btn-danger, .btn-success, .btn-warning"
    );
    downloadBtns.forEach((btn, index) => {
      setTimeout(() => {
        btn.style.animation = "pulse 2s ease-in-out";
      }, index * 100);
    });
  }, 1000);
});

// Utility functions for global use
window.FetchVideoUtils = {
  showToast: (message, type) => toastManager.show(message, type),
  isValidYouTubeUrl: isValidYouTubeUrl,
  extractVideoId: extractVideoId,
  animateProgressBar: animateProgressBar,
};

// Add CSS animations
const style = document.createElement("style");
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    .card-custom {
        transition: all 0.3s ease;
    }

    .btn-custom {
        position: relative;
        overflow: hidden;
    }

    .btn-custom::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s;
    }

    .btn-custom:hover::before {
        left: 100%;
    }

    .lazy {
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .lazy.loaded {
        opacity: 1;
    }
`;
document.head.appendChild(style);
