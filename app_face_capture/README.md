# Face Capture Client Application

A cross-platform Flutter application designed to capture high-quality face photographs for student and instructor registration. Captured photos are validated and registered into the Face Recognition Attendance System database.

## Features

- **Automated Capture Flow**: Captures 10 face photos sequentially with progress feedback.
- **Preparation Countdown**: Initiates a 3-second countdown overlay on camera startup to let the user align their face correctly.
- **Dynamic Transmission Methods**:
  - **Option 1 (Via Server API)**: Uploads photos directly to the `ai_server` registration endpoint and polls the server for face quality validation.
  - **Option 2 (Direct to Supabase)**: Uploads photo files directly to configured Supabase Storage, bypassing the server API for uploads.
- **Admin Control Panel**: Hidden portal protected by a PIN code allowing administrators to trigger manual training of the facial recognition model on the server.
- **Settings Screen**: Easily configure the server's base URL and toggle between the image transmission methods.
- **Local Settings Persistence**: Keeps the server URL and selected upload method saved locally via `SharedPreferences`.

## Architecture & Project Structure

The app follows standard Flutter architecture using the **Provider** pattern for state management and clean separation between UI components and data layers.

```
app_face_capture/
├── lib/
│   ├── core/
│   │   └── constants/                 # Shared Constants (API endpoints, storage paths, PIN)
│   ├── data/
│   │   ├── models/                    # Data models (RegistrationStatus, ValidationResult)
│   │   ├── repositories/              # FaceRepository for routing uploads
│   │   └── services/                  # Supabase Storage & Face API HTTP services
│   ├── presentation/
│   │   ├── viewmodels/                # ViewModels (Admin, Settings, Capture, Upload)
│   │   ├── views/                     # Screens (Home, Settings, Capture, Upload, Admin)
│   │   └── widgets/                   # Reusable UI widgets (Camera preview, overlays, buttons)
│   ├── routing/
│   │   └── app_router.dart            # GoRouter configuration & route guards
│   └── main.dart                      # App entrypoint & provider initializations
├── test/                              # Unit & Widget tests
├── pubspec.yaml                       # App dependencies (supabase_flutter, shared_preferences, etc.)
└── README.md                          # This documentation file
```

## Setup & Installation

### Prerequisites
- Install [Flutter SDK](https://docs.flutter.dev/get-started/install) (latest stable version).
- Setup the Android/iOS simulator or connect a physical device.

### 1. Install Dependencies
```bash
flutter pub get
```

### 2. Configure the Server URL & Supabase
Start the app, navigate to **Settings** (gear icon in the top right), and configure:
1. **Server Base URL**: Set this to your running `ai_server` URL (e.g. `http://10.0.2.2:8000` for Android Emulator, or the local IP of your server).
2. **Supabase Integration**: Set up your Supabase project credentials in your environment/configs if using Direct Supabase upload.

### 3. Run the App
```bash
flutter run
```

### 4. Admin Portal Access
- Open the application.
- **Long-press the app logo** on the Home Screen.
- Enter the admin PIN (defined in `api_constants.dart`) to access the model training page.

## Running Tests
Run the unit test suite to verify the application services, route guards, and view models:
```bash
flutter test
```
