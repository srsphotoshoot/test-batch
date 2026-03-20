import React, { useEffect, useRef } from 'react';

const BubbleBackground = () => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let animationFrameId;

        // Configuration
        const bubbleCount = 150; // Increased density
        const connectionDistance = 120;
        const mouseDistance = 300; // Increased range

        // Neon Palette
        const colors = [
            'rgba(6, 182, 212, 0.6)', // Cyan
            'rgba(139, 92, 246, 0.6)', // Purple
            'rgba(236, 72, 153, 0.6)', // Pink
            'rgba(59, 130, 246, 0.6)'  // Blue
        ];

        let bubbles = [];
        let mouse = { x: -1000, y: -1000 };

        // Resize Canvas
        const handleResize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            initBubbles();
        };

        // Bubble Class
        class Bubble {
            constructor() {
                this.init(true);
            }

            init(randomY = false) {
                this.x = Math.random() * canvas.width;
                this.y = randomY ? Math.random() * canvas.height : canvas.height + 10;
                this.vx = (Math.random() - 0.5) * 1.1; // Was 1.5 (0.75x)
                this.vy = -(Math.random() * 1.5 + 0.75); // Was 2 + 1
                this.radius = Math.random() * 4 + 2;
                this.color = colors[Math.floor(Math.random() * colors.length)];
                this.originalRadius = this.radius;
            }

            draw() {
                ctx.beginPath();
                // Optimization: Use Radial Gradient instead of Box Shadow for performance
                const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.radius);
                gradient.addColorStop(0, this.color);
                gradient.addColorStop(1, 'rgba(0,0,0,0)');

                ctx.fillStyle = gradient;
                // ctx.shadowBlur = 15; // REMOVED: Expensive operation
                ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2, false);
                ctx.fill();
            }

            update() {
                // Apply Velocity
                this.x += this.vx;
                this.y += this.vy;

                // Constant Upward Drift (Buoyancy) - Reduced speed
                this.vy -= 0.035; // Was 0.05 (0.75x)

                // Speed Limit
                const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
                if (speed > 6) { // Was 8
                    this.vx *= 0.9;
                    this.vy *= 0.9;
                }

                // Reset when off top
                if (this.y < -50) {
                    this.init(false);
                }

                // Keep X within bounds
                if (this.x < 0 || this.x > canvas.width) {
                    this.vx = -this.vx;
                }

                // Mouse Interaction
                const dx = mouse.x - this.x;
                const dy = mouse.y - this.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < mouseDistance) {
                    // Attraction Force
                    const forceDirectionX = dx / distance;
                    const forceDirectionY = dy / distance;
                    const force = (mouseDistance - distance) / mouseDistance;

                    // Strong attraction
                    this.vx += forceDirectionX * force * 1.5;
                    this.vy += forceDirectionY * force * 1.5;

                    // Hover Feedback: Slight growth
                    if (this.radius < this.originalRadius * 2.5) {
                        this.radius += 0.5;
                    }
                } else {
                    // Return to normal size
                    if (this.radius > this.originalRadius) {
                        this.radius -= 0.1;
                    }
                }

                this.draw();
            }
        }

        const initBubbles = () => {
            bubbles = [];
            for (let i = 0; i < bubbleCount; i++) {
                bubbles.push(new Bubble());
            }
        };

        const canvasAnimate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear screen

            // Draw all bubbles first
            bubbles.forEach(bubble => bubble.update());

            // Optimize: Batch line drawing (only draw if close)
            ctx.beginPath();
            ctx.lineWidth = 0.5;

            for (let i = 0; i < bubbles.length; i++) {
                const a = bubbles[i];
                // Limit connections to reduce N^2 complexity - only check nearest neighbors effectively? 
                // A simple optimization is to break early? No, spatial partition is best but complex.
                // Simple Optimization: Reduce checking range or just check subsequent indices as is.
                // We'll trust the browser on line rendering but remove individual path creation.

                // Double check loop
                for (let j = i + 1; j < bubbles.length; j++) {
                    const b = bubbles[j];
                    const dx = a.x - b.x;
                    const dy = a.y - b.y;

                    // Fast distance check (manhattan) before sqrt
                    if (Math.abs(dx) > connectionDistance || Math.abs(dy) > connectionDistance) continue;

                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < connectionDistance) {
                        // We must reset path for opacity change unfortunately
                        // Batching with variable opacity is hard. 
                        // Back to individual strokes BUT without shadow overhead it should be faster.
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(255, 255, 255, ${0.5 * (1 - distance / connectionDistance)})`; // Reduced opacity for perf
                        ctx.moveTo(a.x, a.y);
                        ctx.lineTo(b.x, b.y);
                        ctx.stroke();
                    }
                }
            }

            animationFrameId = requestAnimationFrame(canvasAnimate);
        };

        // Event Listeners
        window.addEventListener('resize', handleResize);
        window.addEventListener('mousemove', (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        });

        // Init
        handleResize();
        canvasAnimate();

        return () => {
            window.removeEventListener('resize', handleResize);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                zIndex: -1,
                background: 'transparent',
                pointerEvents: 'none'
            }}
        />
    );
};

export default BubbleBackground;
