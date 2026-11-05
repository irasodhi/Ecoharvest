# EcoHarvest – Sustainable Agriculture & AI Agronomy Platform

## Overview
EcoHarvest is a modern green platform designed to promote sustainable agriculture, organic farming, and ecological crop stewardship. It pairs advanced computer vision and artificial intelligence with an organic farm-to-farm seed marketplace and a cryptographically verified farmer mentorship network.

## Key Capabilities

### 1. Vision & Botanical AI Engine
- **Custom Trained YOLOv8 Architecture**: Identifies 100 agricultural crop, flower, fruit, and leaf classes with bounding boxes and confidence scores.
- **Strict Agricultural Domain Guardrails**: Non-plant objects (such as wallets, electronics, and accessories) are recognized and rejected from classification.
- **Conversational Botanical Chatbot**: Natural language interaction for planting instructions, seasonal care, watering schedules, and live Wikipedia integration.

### 2. Verified Farmer Network & Blockchain Anti-Fraud
- **Cryptographic Document Verification**: Mentors upload authentic state land records (Khasra, Khatauni, 7/12 extract, or Kisan Credit Passbook) sealed on-chain with SHA-256 hashes (`0x...`).
- **Duplicate Prevention**: Rejects duplicate Land Record IDs to prevent falsified farmer identities.
- **Multi-State Coverage**: Mentors categorized across 9 major agricultural states (Haryana, Punjab, Rajasthan, Maharashtra, Uttar Pradesh, Madhya Pradesh, Gujarat, Karnataka, Himachal Pradesh).

### 3. Farm-to-Farm Seed Marketplace
- Direct access to verified organic, non-GMO heirloom seeds.
- Package variants (500g, 1kg, 2kg, 5kg) with live rate recalculation.
- Address persistence and instant checkout autofill across sessions.
- Modern centered toast notifications with auto-dismiss timers.

### 4. User Profile & Order Management
- Order history tracking with live status indicators (`Approved / Dispatched`, `Pending Review`, `Cancelled`).
- Profile photo upload and biography editing.
- Saved shipping address management.
- Account security and cryptographic password updates.

## Technology Stack
- **Backend**: Python 3.11, Flask, Gunicorn
- **Computer Vision**: Ultralytics YOLOv8, OpenCV Headless, Pillow
- **Frontend**: Tailwind CSS, HTML5, Vanilla JavaScript, Jinja2
- **Database**: SQLite3 with auto-migrations
- **Design System**: Dark Emerald Palette, Outfit & DM Sans typography

## Quickstart & Local Setup

```bash
# Clone the repository
git clone https://github.com/irasodhi/11_NovaCoders.git
cd 11_NovaCoders

# Install dependencies
pip install -r requirements.txt

# Start the application server
python app.py
```

Visit `http://127.0.0.1:5000` in your web browser.

## Deployment
Configured for cloud deployment on platforms like Render, Railway, and Heroku via `Procfile`:
```
web: gunicorn app:app
```
