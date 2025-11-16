"""
Frontend Styling Guide - NexusAIPlatform Analytics Platform

This guide documents the styling system and best practices for the frontend application.
Includes Chart.js integration, gradient animations, and custom components.
"""

# ============================================================================
# DESIGN SYSTEM
# ============================================================================

## Color Palette
### Primary Colors
- Primary: #6366f1 (Indigo)
- Primary Hover: #4f46e5
- Primary Light: #818cf8

### Background Colors
- Dark Background: #0f172a (Slate-900)
- Card Background: #1e293b (Slate-800)
- Border Color: #334155 (Slate-700)

### Text Colors
- Primary Text: #f1f5f9 (Slate-100)
- Secondary Text: #94a3b8 (Slate-400)
- Muted Text: #64748b (Slate-500)

### Status Colors
- Success: #10b981 (Green-500)
- Warning: #f59e0b (Amber-500)
- Error: #ef4444 (Red-500)
- Info: #3b82f6 (Blue-500)

## Typography
- Font Family: Inter, system-ui, -apple-system, sans-serif
- Headings: font-weight: 700
- Body: font-weight: 400
- Small Text: font-size: 0.875rem

## Spacing
- Base Unit: 4px
- Small: 8px (0.5rem)
- Medium: 16px (1rem)
- Large: 24px (1.5rem)
- XL: 32px (2rem)

# ============================================================================
# CUSTOM SCROLLBAR
# ============================================================================

Apply this CSS for custom scrollbar styling across all pages:

```css
/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #6366f1 0%, #4f46e5 100%);
  border-radius: 4px;
  transition: background 0.3s ease;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #818cf8 0%, #6366f1 100%);
}

/* Firefox */
* {
  scrollbar-width: thin;
  scrollbar-color: #6366f1 #1e293b;
}
```

# ============================================================================
# GRADIENT BACKGROUNDS
# ============================================================================

## Animated Gradient Background
Use this for hero sections and dashboards:

```css
.gradient-bg {
  background: linear-gradient(
    135deg,
    #667eea 0%,
    #764ba2 25%,
    #f093fb 50%,
    #4facfe 75%,
    #00f2fe 100%
  );
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
```

## Card Gradient Borders
For modern card designs:

```css
.gradient-border {
  position: relative;
  background: #1e293b;
  border-radius: 8px;
  padding: 2px;
}

.gradient-border::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 8px;
  padding: 2px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
}
```

# ============================================================================
# CHART.JS INTEGRATION
# ============================================================================

## Installation
```bash
npm install chart.js react-chartjs-2
```

## Line Chart Component Example
```jsx
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const PerformanceChart = ({ data }) => {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Inference Time (ms)',
        data: data.values,
        fill: true,
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        borderColor: '#6366f1',
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: '#6366f1',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          color: '#f1f5f9',
          font: { size: 12, family: 'Inter' }
        }
      },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f1f5f9',
        bodyColor: '#94a3b8',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 12,
        displayColors: true
      }
    },
    scales: {
      x: {
        grid: { color: '#334155', drawBorder: false },
        ticks: { color: '#94a3b8', font: { size: 11 } }
      },
      y: {
        grid: { color: '#334155', drawBorder: false },
        ticks: { color: '#94a3b8', font: { size: 11 } }
      }
    }
  };

  return <Line data={chartData} options={options} />;
};
```

## Doughnut Chart for Model Distribution
```jsx
import { Doughnut } from 'react-chartjs-2';

const ModelDistributionChart = ({ models }) => {
  const chartData = {
    labels: models.map(m => m.name),
    datasets: [{
      data: models.map(m => m.usage),
      backgroundColor: [
        '#6366f1',
        '#8b5cf6',
        '#ec4899',
        '#f59e0b',
        '#10b981'
      ],
      borderColor: '#1e293b',
      borderWidth: 2
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#f1f5f9',
          padding: 15,
          font: { size: 12 }
        }
      }
    }
  };

  return <Doughnut data={chartData} options={options} />;
};
```

# ============================================================================
# ANIMATIONS
# ============================================================================

## Fade In Animation
```css
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fadeIn 0.5s ease-out;
}
```

## Slide In Animation
```css
@keyframes slideIn {
  from {
    transform: translateX(-100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.slide-in {
  animation: slideIn 0.3s ease-out;
}
```

## Pulse Animation (for status indicators)
```css
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.05);
  }
}

.pulse {
  animation: pulse 2s ease-in-out infinite;
}
```

## Shimmer Loading Effect
```css
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.shimmer {
  background: linear-gradient(
    90deg,
    #1e293b 0%,
    #334155 20%,
    #1e293b 40%,
    #1e293b 100%
  );
  background-size: 1000px 100%;
  animation: shimmer 2s linear infinite;
}
```

# ============================================================================
# COMPONENT PATTERNS
# ============================================================================

## Glass morphism Cards
```jsx
<div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-lg p-6 shadow-xl">
  <h3 className="text-xl font-bold mb-4">Glassmorphism Card</h3>
  <p>Content goes here</p>
</div>
```

## Hover Effects
```css
.hover-lift {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.hover-lift:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
}
```

## Loading Spinner
```jsx
const Spinner = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4'
  };

  return (
    <div className={`
      ${sizeClasses[size]}
      border-gray-700
      border-t-indigo-500
      rounded-full
      animate-spin
    `} />
  );
};
```

# ============================================================================
# RESPONSIVE DESIGN
# ============================================================================

## Breakpoints (Tailwind CSS)
- sm: 640px
- md: 768px
- lg: 1024px
- xl: 1280px
- 2xl: 1536px

## Mobile-First Approach
Always design for mobile first, then scale up:

```jsx
<div className="
  grid
  grid-cols-1
  md:grid-cols-2
  lg:grid-cols-3
  xl:grid-cols-4
  gap-4
">
  {/* Cards */}
</div>
```

# ============================================================================
# ACCESSIBILITY
# ============================================================================

## Focus Styles
```css
*:focus {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

.focus-ring {
  @apply focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900;
}
```

## ARIA Labels
Always include aria-labels for interactive elements:

```jsx
<button aria-label="Close modal" onClick={onClose}>
  <XIcon className="w-5 h-5" />
</button>
```

# ============================================================================
# PERFORMANCE TIPS
# ============================================================================

1. Use CSS transforms instead of position changes for animations
2. Implement virtual scrolling for long lists (react-window)
3. Lazy load images with loading="lazy"
4. Use React.memo() for expensive components
5. Implement code splitting with React.lazy()
6. Use IntersectionObserver for triggering animations
7. Optimize Chart.js by decimating data points

# ============================================================================
# IMPLEMENTATION CHECKLIST
# ============================================================================

## Global Styles (index.css)
- [ ] Custom scrollbar
- [ ] Base color variables
- [ ] Typography system
- [ ] Animation keyframes
- [ ] Utility classes

## Dashboard Page
- [ ] Add gradient background
- [ ] Implement Chart.js for analytics
- [ ] Add pulse animation to status indicators
- [ ] Apply hover lift effects to cards

## Analytics Page
- [ ] Line charts for performance metrics
- [ ] Doughnut chart for model distribution
- [ ] Bar chart for usage statistics
- [ ] Real-time data updates

## ML Models Page
- [ ] Card gradient borders
- [ ] Shimmer loading effect
- [ ] Model upload progress animation

## All Pages
- [ ] Fade-in animations on mount
- [ ] Consistent spacing
- [ ] Responsive grid layouts
- [ ] Accessibility improvements

