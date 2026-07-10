# AquaSense Frontend Client

This is the Next.js client dashboard application for the AquaSense IoT platform.

## Features

- **Live Telemetry Stream:** Consumes Server-Sent Events (SSE) from the backend to display real-time sensor charts, gauges, and notifications.
- **Admin Panel:** Controls users, user roles, and triggers machine learning model retraining.
- **User Settings:** Configures ThingSpeak integration keys and contact details.

## Setup & Run

1. Install Node.js dependencies:
   ```bash
   npm install
   ```

2. Configure environment variables:
   - Copy `.env.example` to `.env.local`
   - Fill in Supabase public API endpoint keys and backend API url.

3. Run development server:
   ```bash
   npm run dev
   ```
