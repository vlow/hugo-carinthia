+++
date = '2023-03-20T20:33:02+02:00'
draft = false
title = 'Social Media Unified Dashboard'
status = 'cemetery' # current or cemetery
tags = ['React', 'Node.js', 'API', 'social-media']
categories = []
github = '' # GitHub repository URL
website = '' # Project website URL
+++

## Overview
Brief description of the project.

## Intentions
What you set out to achieve.

## Learnings
Key insights and takeaways.

## Technical Details
Technology stack, architecture, challenges faced.

## Status
Current state of the project.
An ambitious attempt to create a unified dashboard for managing multiple social media accounts, ultimately abandoned due to API limitations and changing requirements.

## Overview
This project was designed to aggregate content from Twitter, Instagram, LinkedIn, and Facebook into a single management interface. The goal was to streamline social media management for content creators and small businesses.

## Intentions
- Unified posting across multiple platforms
- Analytics dashboard with cross-platform insights
- Content scheduling and automation
- Engagement tracking and response management
- Brand consistency tools

## Technical Details
Built with React frontend and Node.js backend. Integrated with multiple social media APIs including Twitter API v2, Instagram Basic Display API, and Facebook Graph API.

**Tech Stack:**
- Frontend: React, Material-UI, Chart.js
- Backend: Node.js, Express, MongoDB
- Authentication: OAuth 2.0 for each platform
- Deployment: Docker containers on AWS

## Learnings
**What Went Wrong:**
- API rate limits were more restrictive than anticipated
- Instagram severely limited third-party posting capabilities
- Twitter API pricing changes made the project economically unviable
- Each platform had different content requirements and formats

**Key Insights:**
- Always validate API limitations before committing to a project
- Social media platforms prioritize their own tools over third-party integrations
- The regulatory landscape for social media APIs changes rapidly
- User authentication complexity grows exponentially with each platform

## Status
**Abandoned in April 2023.** The project became unfeasible when Twitter introduced API pricing and Instagram tightened their posting restrictions. The core concept was sound, but the external dependencies proved too unstable for a reliable product.
