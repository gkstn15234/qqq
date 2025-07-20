// Main JavaScript functionality for PostUp

document.addEventListener('DOMContentLoaded', function() {
    initializeReadingProgress();
    initializeDarkMode();
    initializeSearch();
    initializeSocialShare();
    initializeUpNext();
    initializeNewsletter();
    initializeClickableCards();
    initializeEnhancedUpNext();
    // 접근성 향상
    initializeAccessibility();
    // H5 세로 막대기 스타일링
    initializeH5Styling();
    // 메인페이지 기사 랜덤 배치
    initializeRandomArticles();
});

// Reading Progress Bar
function initializeReadingProgress() {
    const progressBar = document.getElementById('reading-progress');
    if (!progressBar) return;

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight;
        const clientHeight = document.documentElement.clientHeight;
        const scrollPercentage = (scrollTop / (scrollHeight - clientHeight)) * 100;
        
        progressBar.style.width = Math.min(scrollPercentage, 100) + '%';
    });
}

// Dark Mode Toggle
function initializeDarkMode() {
    const darkModeToggle = document.querySelector('.dark-mode-toggle');
    const currentTheme = localStorage.getItem('theme');
    
    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        updateDarkModeIcon(currentTheme === 'dark');
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }
}

function toggleDarkMode() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateDarkModeIcon(newTheme === 'dark');
}

function updateDarkModeIcon(isDark) {
    const icon = document.querySelector('.dark-mode-toggle i');
    if (icon) {
        icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Search Functionality
function initializeSearch() {
    const searchForm = document.querySelector('.search-form');
    const searchInput = document.getElementById('searchInput');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            performSearch(searchInput.value);
        });
    }
}

function performSearch(query) {
    if (!query.trim()) return;
    
    // Simple client-side search implementation
    // In a real implementation, this would connect to a search API
    const searchUrl = `/search/?q=${encodeURIComponent(query)}`;
    window.location.href = searchUrl;
}

// Social Share Functions
function initializeSocialShare() {
    // Social share buttons are handled by the shareArticle function
    // called from the HTML buttons
}

function shareArticle(platform) {
    const url = encodeURIComponent(window.location.href);
    const title = encodeURIComponent(document.title);
    const description = encodeURIComponent(document.querySelector('meta[name="description"]')?.content || '');
    
    let shareUrl = '';
    
    switch(platform) {
        case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
            break;
        case 'naver':
            shareUrl = `https://share.naver.com/web/shareView.nhn?url=${url}&title=${title}`;
            break;
        case 'copy':
            copyToClipboard(window.location.href);
            showNotification('링크가 복사되었습니다!');
            return;
    }
    
    if (shareUrl) {
        window.open(shareUrl, '_blank', 'width=600,height=400');
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
    }
}

function showNotification(message) {
    // Create and show a temporary notification
    const notification = document.createElement('div');
    notification.className = 'alert alert-success position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 250px;';
    notification.innerHTML = `
        <i class="fas fa-check-circle"></i> ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

// Up Next Article Recommendation
function initializeUpNext() {
    const upNext = document.getElementById('upNext');
    if (!upNext) return;
    
    // Get related articles from the page
    const relatedArticles = document.querySelectorAll('.related-articles .article-card');
    if (relatedArticles.length === 0) return;
    
    let currentScrollPosition = 0;
    
    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight;
        const clientHeight = document.documentElement.clientHeight;
        const scrollPercentage = (scrollTop / (scrollHeight - clientHeight)) * 100;
        
        // Show up next when user scrolled 70% of the article
        if (scrollPercentage > 70 && relatedArticles.length > 0) {
            showUpNext(relatedArticles[0]);
        } else {
            hideUpNext();
        }
        
        currentScrollPosition = scrollTop;
    });
}

function showUpNext(articleElement) {
    const upNext = document.getElementById('upNext');
    if (!upNext) return;
    
    const nextArticleContent = document.getElementById('nextArticleContent');
    if (nextArticleContent && !nextArticleContent.innerHTML) {
        // Extract article information
        const titleElement = articleElement.querySelector('.card-title a');
        const imageElement = articleElement.querySelector('.card-img-top');
        const categoryElement = articleElement.querySelector('.category-badge');
        const descElement = articleElement.querySelector('.card-text');
        
        if (titleElement) {
            const title = titleElement.textContent;
            const href = titleElement.href;
            const imageSrc = imageElement ? imageElement.src : '';
            const category = categoryElement ? categoryElement.textContent : '';
            const description = descElement ? descElement.textContent : '';
            
            nextArticleContent.innerHTML = `
                <div class="next-article-preview" onclick="window.location.href='${href}'">
                    ${imageSrc ? `<img src="${imageSrc}" alt="${title}" class="next-article-image">` : ''}
                    <div class="next-article-info">
                        ${category ? `<span class="next-category-badge">${category}</span>` : ''}
                        <h6 class="next-article-title">${title}</h6>
                        ${description ? `<p class="next-article-desc">${description.substring(0, 80)}...</p>` : ''}
                    </div>
                </div>
            `;
        }
    }
    
    upNext.style.display = 'block';
    upNext.style.opacity = '1';
}

function hideUpNext() {
    const upNext = document.getElementById('upNext');
    if (upNext) {
        upNext.style.display = 'none';
        upNext.style.opacity = '0';
    }
}

// Newsletter Subscription
function initializeNewsletter() {
    const newsletterForms = document.querySelectorAll('.newsletter-form');
    
    newsletterForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const emailInput = form.querySelector('input[type="email"]');
            const email = emailInput.value.trim();
            
            if (validateEmail(email)) {
                subscribeNewsletter(email);
                emailInput.value = '';
            } else {
                showNotification('올바른 이메일 주소를 입력해주세요.');
            }
        });
    });
}

// Clickable Cards
function initializeClickableCards() {
    const clickableCards = document.querySelectorAll('.clickable-card');
    
    clickableCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Don't trigger if clicking on an actual link or button
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || 
                e.target.closest('a') || e.target.closest('button')) {
                return;
            }
            
            const href = this.getAttribute('data-href');
            if (href) {
                window.location.href = href;
            }
        });
        
        // Add keyboard support for accessibility
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const href = this.getAttribute('data-href');
                if (href) {
                    window.location.href = href;
                }
            }
        });
        
        // Make card focusable for keyboard navigation
        if (!card.getAttribute('tabindex')) {
            card.setAttribute('tabindex', '0');
        }
    });
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function subscribeNewsletter(email) {
    // In a real implementation, this would send the email to a backend service
    // TODO: Implement backend newsletter subscription
    showNotification('뉴스레터 구독이 완료되었습니다!');
}

// Smooth Scrolling for Anchor Links
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

// Image Lazy Loading (for browsers that don't support loading="lazy")
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // For data-src images (fallback)
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                    }
                    
                    // Add loaded class when image loads
                    img.addEventListener('load', () => {
                        img.classList.add('loaded');
                    });
                    
                    // Handle error case
                    img.addEventListener('error', () => {
                        img.classList.add('loaded'); // Still remove placeholder
                        console.log('Image failed to load:', img.src);
                    });
                    
                    imageObserver.unobserve(img);
                }
            });
        }, {
            root: null,
            rootMargin: '50px', // Load images 50px before they enter viewport
            threshold: 0.1
        });

        // Observe all lazy images
        document.querySelectorAll('img[loading="lazy"], img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Immediate loading for images that are already in viewport
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
        if (img.complete) {
            img.classList.add('loaded');
        } else {
            img.addEventListener('load', () => {
                img.classList.add('loaded');
            });
        }
    });
}

// Performance: Preload critical resources
function preloadCriticalResources() {
    // Preload next page in sequence for better UX
    const nextPageLink = document.querySelector('.pagination .page-item:not(.active) + .page-item .page-link');
    if (nextPageLink) {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = nextPageLink.href;
        document.head.appendChild(link);
    }
    
    // Preload critical images
    const heroImage = document.querySelector('.hero-image img');
    if (heroImage) {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'image';
        link.href = heroImage.src;
        document.head.appendChild(link);
    }
}

// Initialize performance optimizations immediately
initializeLazyLoading();
preloadCriticalResources();

// Initialize performance optimizations with slight delay for non-critical items
setTimeout(() => {
    // Additional performance optimizations can go here
}, 1000);

// 접근성 향상
function initializeAccessibility() {
    // 네비게이션 토글 버튼 접근성
    initializeNavbarToggle();
    
    // 모달 접근성
    initializeModalAccessibility();
    
    // 키보드 네비게이션
    initializeKeyboardNavigation();
}

// 네비게이션 토글 버튼 접근성
function initializeNavbarToggle() {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('#mainNav');
    
    if (navbarToggler && navbarCollapse) {
        // Bootstrap collapse 이벤트 리스너
        navbarCollapse.addEventListener('shown.bs.collapse', function() {
            navbarToggler.setAttribute('aria-expanded', 'true');
        });
        
        navbarCollapse.addEventListener('hidden.bs.collapse', function() {
            navbarToggler.setAttribute('aria-expanded', 'false');
        });
        
        // 초기 상태 설정
        const isExpanded = navbarCollapse.classList.contains('show');
        navbarToggler.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
    }
}

// 모달 접근성
function initializeModalAccessibility() {
    const searchModal = document.querySelector('#searchModal');
    const searchInput = document.querySelector('#searchInput');
    
    if (searchModal && searchInput) {
        // 모달이 열릴 때 검색 입력 필드에 포커스
        searchModal.addEventListener('shown.bs.modal', function() {
            searchInput.focus();
        });
        
        // ESC 키로 모달 닫기 (Bootstrap에서 기본 제공하지만 명시적으로 추가)
        searchModal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const modal = bootstrap.Modal.getInstance(searchModal);
                if (modal) {
                    modal.hide();
                }
            }
        });
    }
}

// 키보드 네비게이션 개선
function initializeKeyboardNavigation() {
    // Skip to content 링크 추가
    addSkipToContentLink();
    
    // 탭 트랩핑 (모달에서)
    addModalTabTrapping();
}

// Skip to content 링크
function addSkipToContentLink() {
    const skipLink = document.createElement('a');
    skipLink.className = 'skip-to-content';
    skipLink.href = '#main-content';
    skipLink.textContent = '본문으로 건너뛰기';
    skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 6px;
        background: #000;
        color: #fff;
        padding: 8px 12px;
        text-decoration: none;
        z-index: 9999;
        border-radius: 4px;
        font-weight: bold;
        transition: top 0.3s ease;
    `;
    
    skipLink.addEventListener('focus', function() {
        this.style.top = '6px';
    });
    
    skipLink.addEventListener('blur', function() {
        this.style.top = '-40px';
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // 메인 콘텐츠에 id 추가 (없는 경우)
    const mainContent = document.querySelector('main, .main-content, #main');
    if (mainContent && !mainContent.id) {
        mainContent.id = 'main-content';
    }
}

// 모달 내 탭 트랩핑
function addModalTabTrapping() {
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(modal => {
        modal.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                trapTabKey(e, modal);
            }
        });
    });
}

// 탭 키 트랩핑 함수
function trapTabKey(e, modal) {
    const focusableElements = modal.querySelectorAll(
        'a[href]:not([disabled]), button:not([disabled]), textarea:not([disabled]), input[type="text"]:not([disabled]), input[type="radio"]:not([disabled]), input[type="checkbox"]:not([disabled]), select:not([disabled])'
    );
    
    const firstTabStop = focusableElements[0];
    const lastTabStop = focusableElements[focusableElements.length - 1];
    
    if (e.shiftKey) {
        if (document.activeElement === firstTabStop) {
            e.preventDefault();
            lastTabStop.focus();
        }
    } else {
        if (document.activeElement === lastTabStop) {
            e.preventDefault();
            firstTabStop.focus();
        }
    }
}

// 접근성 알림 (스크린 리더용)
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

// Enhanced Up Next Article Recommendation
function initializeEnhancedUpNext() {
    const upNext = document.getElementById('upNext');
    if (!upNext) return;
    
    // Get related articles from the page
    const relatedArticles = document.querySelectorAll('.related-articles .article-card');
    if (relatedArticles.length === 0) return;
    
    let isUpNextVisible = false;
    
    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight;
        const clientHeight = document.documentElement.clientHeight;
        const scrollPercentage = (scrollTop / (scrollHeight - clientHeight)) * 100;
        
        // Show up next when user scrolled 70% of the article
        if (scrollPercentage > 70 && relatedArticles.length > 0 && !isUpNextVisible) {
            showEnhancedUpNext(relatedArticles[0]);
            isUpNextVisible = true;
        } else if (scrollPercentage <= 70 && isUpNextVisible) {
            hideEnhancedUpNext();
            isUpNextVisible = false;
        }
    });
}

function showEnhancedUpNext(articleElement) {
    const upNext = document.getElementById('upNext');
    if (!upNext) return;
    
    const nextArticleContent = document.getElementById('nextArticleContent');
    if (!nextArticleContent) return;
    
    // Extract article information
    const titleElement = articleElement.querySelector('.card-title a');
    const imageElement = articleElement.querySelector('.card-img-top');
    const categoryElement = articleElement.querySelector('.category-badge');
    const descElement = articleElement.querySelector('.card-text');
    
    if (titleElement) {
        const title = titleElement.textContent.trim();
        const href = titleElement.href;
        const imageSrc = imageElement ? imageElement.src : '';
        const category = categoryElement ? categoryElement.textContent.trim() : '';
        const description = descElement ? descElement.textContent.trim() : '';
        
        nextArticleContent.innerHTML = `
            <div class="next-article-preview" onclick="window.location.href='${href}'" style="cursor: pointer;">
                ${imageSrc ? `<img src="${imageSrc}" alt="${title}" class="next-article-image" loading="lazy">` : ''}
                <div class="next-article-info">
                    ${category ? `<span class="next-category-badge">${category}</span>` : ''}
                    <h6 class="next-article-title">${title}</h6>
                    ${description ? `<p class="next-article-desc">${description.substring(0, 120)}...</p>` : ''}
                </div>
            </div>
        `;
    }
    
    upNext.style.display = 'block';
    upNext.classList.add('show');
}

function hideEnhancedUpNext() {
    const upNext = document.getElementById('upNext');
    if (upNext) {
        upNext.classList.remove('show');
        setTimeout(() => {
            upNext.style.display = 'none';
        }, 300); // Wait for animation to complete
    }
}

// ===== CLS 최적화: 이미지 로딩 상태 관리 =====

// 이미지 로딩 완료 감지 및 스켈레톤 제거
function optimizeImageLoading() {
    const images = document.querySelectorAll('img[loading="lazy"], img[loading="eager"]');
    
    images.forEach(img => {
        // 이미지가 이미 로드된 경우
        if (img.complete && img.naturalHeight !== 0) {
            img.classList.add('loaded');
            removeSkeletonLoader(img);
        } else {
            // 이미지 로드 이벤트 리스너
            img.addEventListener('load', function() {
                this.classList.add('loaded');
                removeSkeletonLoader(this);
            });
            
            // 이미지 로드 실패 시 처리
            img.addEventListener('error', function() {
                this.classList.add('error');
                removeSkeletonLoader(this);
                showImagePlaceholder(this);
            });
        }
    });
}

// 스켈레톤 로더 제거
function removeSkeletonLoader(img) {
    const container = img.closest('.article-image, .article-thumb, .article-main-image, .card-img-wrapper');
    if (container) {
        const skeleton = container.querySelector('::before');
        if (skeleton) {
            container.style.setProperty('--skeleton-display', 'none');
        }
    }
}

// 이미지 플레이스홀더 표시
function showImagePlaceholder(img) {
    const placeholder = document.createElement('div');
    placeholder.className = 'image-placeholder';
    placeholder.innerHTML = '<i class="fas fa-image"></i>';
    placeholder.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #f8f9fa;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        color: #6c757d;
    `;
    
    const container = img.parentElement;
    if (container) {
        container.appendChild(placeholder);
        img.style.opacity = '0';
    }
}

// 폰트 로딩 최적화
function optimizeFontLoading() {
    // 폰트 로딩 상태 감지
    if ('fonts' in document) {
        document.fonts.ready.then(() => {
            document.body.classList.add('fonts-loaded');
        });
        
        // 주요 폰트 미리 로드
        const fontFace = new FontFace('Noto Sans KR', 'url(https://fonts.gstatic.com/s/notosanskr/v27/PbykFmXiEBPT4ITbgNA5Cgm20xz64px_1hVWr0wuPNGmlQNMEfD4.woff2)');
        fontFace.load().then(() => {
            document.fonts.add(fontFace);
            document.body.classList.add('primary-font-loaded');
        }).catch(() => {
            // 폰트 로딩 실패 시 웹 폰트 대신 시스템 폰트 사용
            document.body.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        });
    }
}

// 레이아웃 안정성 모니터링
function monitorLayoutStability() {
    if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.entryType === 'layout-shift' && !entry.hadRecentInput) {
                    console.log('Layout shift detected:', entry.value);
                    
                    // 큰 레이아웃 시프트가 감지되면 최적화 실행
                    if (entry.value > 0.1) {
                        optimizeLayout();
                    }
                }
            }
        });
        
        observer.observe({ type: 'layout-shift', buffered: true });
    }
}

// 레이아웃 최적화 실행
function optimizeLayout() {
    // 모든 이미지 컨테이너에 고정 크기 적용
    const containers = document.querySelectorAll('.article-image, .article-thumb, .card-img-wrapper');
    containers.forEach(container => {
        if (!container.style.minHeight) {
            const img = container.querySelector('img');
            if (img) {
                const rect = container.getBoundingClientRect();
                if (rect.height > 0) {
                    container.style.minHeight = rect.height + 'px';
                }
            }
        }
    });
    
    // 텍스트 컨테이너 최적화
    const textContainers = document.querySelectorAll('.article-content, .card-body');
    textContainers.forEach(container => {
        const rect = container.getBoundingClientRect();
        if (rect.height > 0 && !container.style.minHeight) {
            container.style.minHeight = rect.height + 'px';
        }
    });
}

// 동적 콘텐츠 로딩 최적화
function optimizeDynamicContent() {
    // 광고나 동적 콘텐츠 영역에 플레이스홀더 적용
    const dynamicElements = document.querySelectorAll('.ad-container, .dynamic-content, [data-dynamic]');
    dynamicElements.forEach(element => {
        if (!element.style.minHeight) {
            element.style.minHeight = '200px';
            element.style.backgroundColor = '#f8f9fa';
            element.style.border = '1px dashed #dee2e6';
        }
    });
}

// Intersection Observer를 이용한 지연 로딩 최적화
function setupAdvancedLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // 이미지 소스 설정 전 컨테이너 크기 고정
                    const container = img.closest('.article-image, .article-thumb, .card-img-wrapper');
                    if (container && !container.style.minHeight) {
                        const rect = container.getBoundingClientRect();
                        if (rect.height > 0) {
                            container.style.minHeight = rect.height + 'px';
                        }
                    }
                    
                    // 이미지 소스 설정
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });
        
        // 지연 로딩 이미지 관찰 시작
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
}

// 페이지 로드 시 CLS 최적화 실행
document.addEventListener('DOMContentLoaded', function() {
    optimizeImageLoading();
    optimizeFontLoading();
    optimizeDynamicContent();
    setupAdvancedLazyLoading();
    
    // 완전 투명한 CLS 방지 시스템
    invisibleCLSPrevention();
    
    // 레이아웃 안정성 모니터링 (개발 모드에서만)
    if (window.location.hostname === 'localhost' || window.location.hostname.includes('preview')) {
        monitorLayoutStability();
    }
});

// 완전 투명한 CLS 방지 - 디자인 무변경
function invisibleCLSPrevention() {
    // 1. 모든 이미지에 width/height 속성 확보
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        if (!img.hasAttribute('width') || !img.hasAttribute('height')) {
            const container = img.parentElement;
            if (container) {
                const computedStyle = window.getComputedStyle(container);
                const containerWidth = container.offsetWidth;
                
                // 컨테이너 크기 기반으로 적절한 비율 설정
                if (img.closest('.main-news-image, .main-article .article-image')) {
                    img.setAttribute('width', containerWidth);
                    img.setAttribute('height', Math.round(containerWidth * 9 / 16));
                } else if (img.closest('.side-news-image, .right-news-image')) {
                    img.setAttribute('width', containerWidth);
                    img.setAttribute('height', Math.round(containerWidth * 10 / 16));
                } else if (img.closest('.secondary-news-image, .bottom-news-image')) {
                    img.setAttribute('width', containerWidth);
                    img.setAttribute('height', Math.round(containerWidth * 3 / 4));
                } else {
                    img.setAttribute('width', containerWidth);
                    img.setAttribute('height', Math.round(containerWidth * 10 / 16));
                }
            }
        }
    });
    
    // 2. 폰트 로딩 완료까지 텍스트 영역 고정
    if ('fonts' in document) {
        document.fonts.ready.then(() => {
            // 폰트 로딩 완료 후 추가 작업 없음 (자연스러운 렌더링)
        });
    }
    
    // 3. 컨테이너 크기 사전 확보 (보이지 않게)
    const containers = document.querySelectorAll('.main-news-article, .side-news-card, .right-news-card, .card');
    containers.forEach(container => {
        const style = window.getComputedStyle(container);
        if (style.height === 'auto' || !style.height) {
            container.style.minHeight = '1px'; // 최소한의 크기 확보
        }
    });
    
    // 4. 스크롤 위치 보존
    const scrollPosition = window.scrollY;
    requestAnimationFrame(() => {
        if (Math.abs(window.scrollY - scrollPosition) > 5) {
            window.scrollTo(0, scrollPosition);
        }
    });
}

// 페이지 완전 로드 후 최종 최적화
window.addEventListener('load', function() {
    // 모든 이미지 로딩 상태 재확인
    setTimeout(() => {
        optimizeImageLoading();
        optimizeLayout();
    }, 100);
});

// 리사이즈 시 레이아웃 재최적화
window.addEventListener('resize', debounce(function() {
    optimizeLayout();
}, 250));

// 디바운스 함수
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// H5 세로 막대기 스타일링 초기화
function initializeH5Styling() {
    const h5Elements = document.querySelectorAll('.entry-content h5');
    
    h5Elements.forEach(h5 => {
        const text = h5.textContent || h5.innerText;
        
        // 세로 막대기(|)가 포함된 H5에 특별 스타일 적용
        if (text.includes('|')) {
            h5.classList.add('has-pipe');
            
            // 세로 막대기 문자를 색상이 있는 span으로 감싸기
            const htmlContent = h5.innerHTML;
            const styledContent = htmlContent.replace(/\|/g, '<span style="color: var(--accent-color); font-weight: bold; margin-right: 8px;">|</span>');
            h5.innerHTML = styledContent;
        }
    });
}

// 메인페이지 기사 랜덤 배치 초기화
function initializeRandomArticles() {
    // 메인페이지에서만 실행
    if (window.location.pathname !== '/') return;
    
    // 기사 요소들을 가져오기
    const featuredSection = document.querySelector('.featured-section .row');
    const latestSection = document.querySelector('.latest-articles');
    const mobileSection = document.querySelector('.row.g-4.d-md-none');
    
    // 추가적인 랜덤성을 위해 CSS 애니메이션 클래스 추가
    if (featuredSection) {
        featuredSection.classList.add('fade-in-random');
    }
    if (latestSection) {
        latestSection.classList.add('fade-in-random');
    }
    if (mobileSection) {
        mobileSection.classList.add('fade-in-random');
    }
    
    // 시각적 효과를 위한 스타일 추가
    addRandomArticleStyles();
}

// 랜덤 기사 표시를 위한 CSS 스타일 동적 추가
function addRandomArticleStyles() {
    if (document.getElementById('random-articles-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'random-articles-styles';
    style.textContent = `
        .fade-in-random {
            animation: fadeInUp 0.6s ease-out;
        }
        
        .fade-in-random > * {
            animation: fadeInStagger 0.8s ease-out;
            animation-fill-mode: both;
        }
        
        .fade-in-random > *:nth-child(1) { animation-delay: 0.1s; }
        .fade-in-random > *:nth-child(2) { animation-delay: 0.2s; }
        .fade-in-random > *:nth-child(3) { animation-delay: 0.3s; }
        .fade-in-random > *:nth-child(4) { animation-delay: 0.4s; }
        .fade-in-random > *:nth-child(5) { animation-delay: 0.5s; }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes fadeInStagger {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
}
