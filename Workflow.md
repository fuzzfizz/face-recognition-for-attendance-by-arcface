# Project Restructuring Plan

This document outlines the architectural restructuring for the `@ai_server\` and `@app_face_capture\` modules. The server serves as the AI engine and API gateway, mediating communication between the client application, the external database, and the ESP32 hardware module.

---

## 1. Server-Side Architecture (`@ai_server\`)

### 1.1 Database Configuration

- **No Local Database:** The server will not host a local database instance.
- **Environment Variables:** External database connections and credentials must be configured strictly via a `.env` file.

### 1.2 Core Functions

The server handles two primary workflows: **Face Registration (Model Training)** and **Face Verification**.

#### A. Face Registration & Model Training

The system trains the facial recognition model using two distinct image ingestion workflows:

1. **API-Driven Ingestion (From App):**
   - Receives images from the application via a dedicated API endpoint.
   - Converts the incoming images into numerical vectors.
   - Saves the numerical vectors directly into the external database.
2. **Database-Driven Ingestion (Timeframe Fetching):**
   - Retrieves historical or batch images directly from the database based on administrator-specified timeframes.
   - Executes the model training process on these images.
   - Saves the resulting trained model locally as a `.pkl` file on the server.
   - Extracts and writes the corresponding numerical vectors back into the database.

#### B. Admin Commands

- **Immediate Training Trigger:** An administrative API endpoint is provided to trigger the training process immediately.
- **Constraint:** This immediate training command is **only** compatible with the database-driven ingestion method (fetching images via specified timeframes from the database).

#### C. Face Verification

- **Hardware Integration:** Receives real-time images captured and sent by the ESP32 module via a verification API endpoint.
- **AI Processing:** The server-side AI processes the image to perform facial verification.
- **Output & Logging:** Returns the identified person's name to the requester and automatically logs an attendance record into the external database.

---

## 2. Application-Side Architecture (`@app_face_capture\`)

The primary objective of the application is data collection, specifically capturing high-quality photographs suitable for facial recognition from registering students and instructors.

### 2.1 Image Transmission Methods

The application must support two selectable methods for transmitting captured registration photos:

1. **Option 1 (Via Server API):** Transmits photos directly to the `@ai_server\` API endpoint for processing and vector storage.
2. **Option 2 (Direct to Database):** Bypasses the server API for initial image storage and writes the photo data directly into the configured database.
