+++
title = 'Quick CSS Tip'
date = 2025-09-06T11:30:00-07:00
draft = false
tags = ['css', 'tips']
+++

Just discovered this neat CSS trick for responsive typography:

```css
font-size: clamp(1rem, 2.5vw, 1.5rem);
```

Perfect for maintaining readable text across all device sizes without media queries!