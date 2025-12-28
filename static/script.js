// Prize values (must match backend) - 30 is Jackpot
const PRIZES = [1, 5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100];
const SEGMENTS = PRIZES.length;
const SEGMENT_ANGLE = 360 / SEGMENTS;

let isSpinning = false;
let hasSpun = false;

// Initialize canvas
const canvas = document.getElementById('wheelCanvas');
const ctx = canvas.getContext('2d');

// Optimize canvas for better performance
ctx.imageSmoothingEnabled = true;
ctx.imageSmoothingQuality = 'high';

// Get initial canvas size (will be adjusted in drawWheel)
let centerX = canvas.width / 2;
let centerY = canvas.height / 2;
let radius = Math.min(centerX, centerY) - 10;

// Colors for segments
const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
    '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
    '#F8B739', '#52BE80', '#EC7063', '#5DADE2'
];

// Draw wheel
function drawWheel() {
    // Handle canvas size for mobile - bigger size for responsive view
    const isMobile = window.innerWidth <= 768;
    const canvasSize = isMobile ? 300 : 280;
    canvas.width = canvasSize;
    canvas.height = canvasSize;
    
    centerX = canvas.width / 2;
    centerY = canvas.height / 2;
    radius = Math.min(centerX, centerY) - 10;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    for (let i = 0; i < SEGMENTS; i++) {
        const startAngle = (i * SEGMENT_ANGLE - 90) * (Math.PI / 180);
        const endAngle = ((i + 1) * SEGMENT_ANGLE - 90) * (Math.PI / 180);
        
        // Draw segment
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.closePath();
        ctx.fillStyle = colors[i];
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Draw text
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate((startAngle + endAngle) / 2);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        // Adjust font size based on canvas size
        const fontSize = canvas.width <= 300 ? (canvas.width <= 200 ? 12 : 16) : 14;
        ctx.font = `bold ${fontSize}px Arial`;
        // Show "Jackpot" for ₹30, otherwise show ₹amount
        const displayText = PRIZES[i] === 30 ? 'Jackpot' : `₹${PRIZES[i]}`;
        ctx.fillText(displayText, radius * 0.7, 0);
        ctx.restore();
    }
    
    // Draw center circle - adjust size based on canvas
    const centerRadius = canvas.width <= 300 ? (canvas.width <= 200 ? 20 : 30) : 25;
    ctx.beginPath();
    ctx.arc(centerX, centerY, centerRadius, 0, 2 * Math.PI);
    ctx.fillStyle = '#2a5298';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = canvas.width <= 300 ? 3 : 2.5;
    ctx.stroke();
}

// Easing function (ease-out-cubic)
function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}

// Spin wheel animation
function spinWheel(targetPrize) {
    if (isSpinning) return;
    
    isSpinning = true;
    const spinButton = document.getElementById('spinButton');
    spinButton.disabled = true;
    
    // Find target segment index
    const targetIndex = PRIZES.indexOf(targetPrize);
    
    // Segments are drawn starting from -90 degrees (top of canvas)
    // Segment i center angle in canvas coordinates: (i * SEGMENT_ANGLE - 90 + SEGMENT_ANGLE/2)
    // Pointer is at top (0 degrees screen = -90 degrees canvas)
    // To move segment center to pointer position, we need to rotate:
    // Rotation = -90 - (segment center angle)
    // = -90 - (i * SEGMENT_ANGLE - 90 + SEGMENT_ANGLE/2)
    // = -i * SEGMENT_ANGLE - SEGMENT_ANGLE/2
    // For positive (clockwise) CSS rotation: 360 - (i * SEGMENT_ANGLE + SEGMENT_ANGLE/2)
    
    const segmentCenterOffset = targetIndex * SEGMENT_ANGLE + (SEGMENT_ANGLE / 2);
    const targetRotation = 360 - segmentCenterOffset;
    
    // Multiple spins for visual effect
    const spins = 5;
    const baseRotation = spins * 360;
    
    // Total rotation needed
    const totalRotation = baseRotation + targetRotation;
    
    let currentRotation = 0;
    const duration = 4000; // 4 seconds
    const startTime = Date.now();
    
    function animate() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easeOutCubic(progress);
        
        currentRotation = totalRotation * easedProgress;
        
        canvas.style.transform = `rotate(${currentRotation}deg)`;
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            // Animation complete - set exact final position
            canvas.style.transform = `rotate(${totalRotation}deg)`;
            setTimeout(() => {
                showResult(targetPrize);
                isSpinning = false;
            }, 500);
        }
    }
    
    animate();
}

// Show result modal
function showResult(prize) {
    const modal = document.getElementById('resultModal');
    const resultMessage = document.getElementById('resultMessage');
    const upiForm = document.getElementById('upiForm');
    const upiInput = document.getElementById('upiInput');
    const upiStatus = document.getElementById('upiStatus');
    
    // Show message
    if (prize === 30) {
        resultMessage.textContent = 'You won Jackpot!';
    } else {
        resultMessage.textContent = `You won ${prize} rupees!`;
    }
    
    // Show UPI form
    upiForm.style.display = 'block';
    upiInput.value = '';
    upiStatus.textContent = '';
    
    modal.classList.add('show');
    
    // Create confetti
    createConfetti();
}

// Create confetti animation
function createConfetti() {
    const container = document.getElementById('confetti-container');
    const colors = ['#d4af37', '#f4d03f', '#ffd700', '#ffed4e'];
    
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.animationDelay = Math.random() * 0.5 + 's';
            container.appendChild(confetti);
            
            setTimeout(() => {
                confetti.remove();
            }, 3000);
        }, i * 20);
    }
}

// Close modal
function closeModal() {
    const modal = document.getElementById('resultModal');
    modal.classList.remove('show');
}

// Handle order ID validation
document.getElementById('validateOrderBtn').addEventListener('click', async () => {
    const orderIdInput = document.getElementById('orderIdInput');
    const orderStatus = document.getElementById('orderStatus');
    const validateBtn = document.getElementById('validateOrderBtn');
    
    const orderId = orderIdInput.value.trim().toUpperCase();
    
    if (!orderId) {
        orderStatus.textContent = 'Please enter an order ID';
        orderStatus.className = 'order-status error';
        return;
    }
    
    validateBtn.disabled = true;
    validateBtn.textContent = '...';
    orderStatus.textContent = '';
    
    try {
        const response = await fetch('/validate-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ order_id: orderId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            orderStatus.textContent = '✓ Valid';
            orderStatus.className = 'order-status success';
            orderIdInput.style.borderColor = '#52BE80';
            orderIdInput.setAttribute('data-valid', 'true');
            orderIdInput.setAttribute('data-valid-id', orderId);
        } else {
            orderStatus.textContent = data.message || 'Invalid order ID';
            orderStatus.className = 'order-status error';
            orderIdInput.style.borderColor = '#EC7063';
            orderIdInput.removeAttribute('data-valid');
        }
    } catch (error) {
        console.error('Error:', error);
        orderStatus.textContent = 'An error occurred. Please try again.';
        orderStatus.className = 'order-status error';
    } finally {
        validateBtn.disabled = false;
        validateBtn.textContent = '✓';
    }
});

    // Allow Enter key to validate order
document.getElementById('orderIdInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('validateOrderBtn').click();
    }
});

// Clear validation when order ID input changes
document.getElementById('orderIdInput').addEventListener('input', (e) => {
    const orderIdInput = e.target;
    orderIdInput.removeAttribute('data-valid');
    orderIdInput.removeAttribute('data-valid-id');
    orderIdInput.style.borderColor = '';
    const orderStatus = document.getElementById('orderStatus');
    if (orderStatus && !orderStatus.classList.contains('error')) {
        orderStatus.textContent = '';
    }
});

// Handle spin button click
document.getElementById('spinButton').addEventListener('click', async () => {
    if (isSpinning) return;
    
    const orderIdInput = document.getElementById('orderIdInput');
    const orderStatus = document.getElementById('orderStatus');
    const orderId = orderIdInput ? orderIdInput.value.trim().toUpperCase() : '';
    
    // Order ID is required for all spins (to prevent unlimited spins)
    if (!orderId) {
        orderStatus.textContent = 'Please enter Order ID to spin!';
        orderStatus.className = 'order-status error';
        orderIdInput.focus();
        return;
    }
    
    // Check if order ID was validated (has data-valid attribute)
    const isValidated = orderIdInput.getAttribute('data-valid') === 'true';
    const lastValidatedId = orderIdInput.getAttribute('data-valid-id');
    
    // If order ID changed or not validated, validate it first
    if (!isValidated || lastValidatedId !== orderId) {
        try {
            orderStatus.textContent = 'Validating...';
            orderStatus.className = 'order-status';
            
            const validateResponse = await fetch('/validate-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ order_id: orderId })
            });
            
            const validateData = await validateResponse.json();
            
            if (!validateData.success) {
                orderStatus.textContent = validateData.message || 'Invalid order ID. Please check and try again.';
                orderStatus.className = 'order-status error';
                orderIdInput.removeAttribute('data-valid');
                orderIdInput.removeAttribute('data-valid-id');
                orderIdInput.focus();
                return;
            }
            
            // Order ID is valid - show green success message
            orderStatus.textContent = '✓ Valid';
            orderStatus.className = 'order-status success';
            orderIdInput.style.borderColor = '#52BE80';
            orderIdInput.setAttribute('data-valid', 'true');
            orderIdInput.setAttribute('data-valid-id', orderId);
        } catch (error) {
            console.error('Validation error:', error);
            orderStatus.textContent = 'Error validating order ID. Please try again.';
            orderStatus.className = 'order-status error';
            orderIdInput.removeAttribute('data-valid');
            orderIdInput.removeAttribute('data-valid-id');
            return;
        }
    }
    
    try {
        const response = await fetch('/spin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ order_id: orderId || '' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            hasSpun = false; // Reset for new spin with order ID
            if (orderId) {
                // Clear order ID after successful spin
                orderIdInput.value = '';
                orderStatus.textContent = '';
                orderIdInput.removeAttribute('data-valid');
                orderIdInput.removeAttribute('data-valid-id');
                orderIdInput.style.borderColor = '';
            }
            spinWheel(data.prize);
        } else {
            if (orderId) {
                const orderStatusEl = document.getElementById('orderStatus');
                if (orderStatusEl) {
                    orderStatusEl.textContent = data.message || 'Invalid order ID';
                    orderStatusEl.className = 'order-status error';
                }
            } else {
                orderStatus.textContent = data.message || 'You have already used your spin. Enter order ID to spin again!';
                orderStatus.className = 'order-status error';
                hasSpun = true;
                orderIdInput.focus();
            }
        }
    } catch (error) {
        console.error('Error:', error);
        orderStatus.textContent = 'An error occurred. Please try again.';
        orderStatus.className = 'order-status error';
    }
});

// UPI ID validation function
function validateUPI(upiId) {
    // Must have @ symbol
    if (!upiId.includes('@')) {
        return false;
    }
    
    // Split by @
    const parts = upiId.split('@');
    if (parts.length !== 2) {
        return false;
    }
    
    const username = parts[0].trim();
    const provider = parts[1].trim();
    
    // Validate username (before @)
    if (!username || username.length < 2) {
        return false;
    }
    
    // Validate provider (after @)
    if (!provider || provider.length < 2) {
        return false;
    }
    
    // Full pattern validation
    const upiPattern = /^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$/;
    return upiPattern.test(upiId);
}

// Handle UPI submission
document.getElementById('submitUpiBtn').addEventListener('click', async () => {
    const upiInput = document.getElementById('upiInput');
    const upiStatus = document.getElementById('upiStatus');
    const submitBtn = document.getElementById('submitUpiBtn');
    
    const upiId = upiInput.value.trim();
    
    if (!upiId) {
        upiStatus.textContent = 'Please enter your UPI ID';
        upiStatus.className = 'upi-status error';
        return;
    }
    
    // Validate UPI ID format
    if (!upiId.includes('@')) {
        upiStatus.textContent = 'Invalid UPI ID. Must include @ symbol (e.g., yourname@paytm)';
        upiStatus.className = 'upi-status error';
        return;
    }
    
    const parts = upiId.split('@');
    if (parts.length !== 2) {
        upiStatus.textContent = 'Invalid UPI ID format. Use format: yourname@paytm';
        upiStatus.className = 'upi-status error';
        return;
    }
    
    const username = parts[0].trim();
    const provider = parts[1].trim();
    
    if (!username || username.length < 2) {
        upiStatus.textContent = 'Invalid username. Must be at least 2 characters before @';
        upiStatus.className = 'upi-status error';
        return;
    }
    
    if (!provider || provider.length < 2) {
        upiStatus.textContent = 'Invalid provider. Must include provider name after @ (e.g., @paytm, @ybl, @upi)';
        upiStatus.className = 'upi-status error';
        return;
    }
    
    if (!validateUPI(upiId)) {
        upiStatus.textContent = 'Invalid UPI ID format. Use format: yourname@paytm (only letters, numbers, dots, hyphens, underscores allowed)';
        upiStatus.className = 'upi-status error';
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    upiStatus.textContent = '';
    
    try {
        const response = await fetch('/submit-upi', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ upi_id: upiId })
        });
        
        // Check if response is ok
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: 'Server error' }));
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            upiStatus.textContent = data.message;
            upiStatus.className = 'upi-status success';
            upiInput.disabled = true;
            submitBtn.textContent = 'Submitted ✓';
        } else {
            upiStatus.textContent = data.message || 'Error submitting UPI ID';
            upiStatus.className = 'upi-status error';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit UPI ID';
        }
    } catch (error) {
        console.error('Error:', error);
        upiStatus.textContent = error.message || 'An error occurred. Please try again.';
        upiStatus.className = 'upi-status error';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit UPI ID';
    }
});

// Allow Enter key to submit UPI
document.getElementById('upiInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('submitUpiBtn').click();
    }
});

// Close modal on X click
document.querySelector('.close').addEventListener('click', closeModal);

// Close modal on outside click
window.addEventListener('click', (event) => {
    const modal = document.getElementById('resultModal');
    if (event.target === modal) {
        closeModal();
    }
});

// Check user status on page load
async function checkStatus() {
    try {
        const response = await fetch('/check-status');
        const data = await response.json();
        
        if (data.has_spun) {
            hasSpun = true;
            const spinButton = document.getElementById('spinButton');
            
            // Don't disable button - user can use order ID
            // Just show message that they need order ID
            
            if (data.prize) {
                // Optionally show previous result
                setTimeout(() => {
                    showResult(data.prize);
                }, 500);
            }
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Handle window resize for responsive canvas
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (!isSpinning) {
            drawWheel();
        }
    }, 250);
});

// Initialize
drawWheel();
checkStatus();

