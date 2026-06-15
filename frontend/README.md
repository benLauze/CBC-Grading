# CBC Grading — Mobile App

A React Native (Expo) app for scanning and grading Pokémon cards.

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Start the Expo dev server
npx expo start

# 3. Open on device
#    - iOS: Scan QR code with Camera app
#    - Android: Scan QR code with Expo Go app
#    - Simulator: Press 'i' (iOS) or 'a' (Android) in terminal
```

## Project Structure

```
cbc-grading/
├── App.js                          # Navigation root — all screens registered here
├── app.json                        # Expo config (app name, permissions, bundle ID)
├── src/
│   ├── theme.js                    # Colors, typography, grade config
│   ├── components/
│   │   └── ScanViewfinder.js       # Camera component using expo-camera
│   └── screens/
│       ├── HomeScreen.js           # Entry — shows scan checklist + analyze CTA
│       ├── ScanScreen.js           # Shared scan screen (front & back)
│       ├── ProcessingScreen.js     # ⭐ Main backend API call lives here
│       └── ResultsScreen.js        # Displays grade, set, price from API response
```

## Backend Integration

There are **3 integration points**, all clearly marked with comments in the code:

### 1. Image capture — `ScanViewfinder.js`
```js
// After capture, photo.uri is the local file path.
// Switch to base64 for direct API upload:
const photo = await cameraRef.current.takePictureAsync({ base64: true, quality: 0.85 });
```

### 2. API call — `ProcessingScreen.js` (primary integration point)
Replace the mock with your real endpoint:
```js
const callGradingAPI = async () => {
  const formData = new FormData();
  formData.append('front', { uri: frontImage, name: 'front.jpg', type: 'image/jpeg' });
  formData.append('back',  { uri: backImage,  name: 'back.jpg',  type: 'image/jpeg' });

  const response = await fetch('https://your-api.com/grade', {
    method: 'POST',
    body: formData,
    headers: { 'Authorization': 'Bearer YOUR_TOKEN' },
  });
  return response.json();
};
```

### 3. Expected API response shape
Your backend should return JSON matching this shape:
```json
{
  "name": "Charizard VMAX",
  "set": "Sword & Shield — Champion's Path",
  "setCode": "SWSH035",
  "number": "074/073",
  "rarity": "Secret Rare",
  "grade": 9,
  "subgrades": {
    "centering": 9.5,
    "corners": 9.0,
    "edges": 8.5,
    "surface": 9.5
  },
  "price": {
    "market": 189.99,
    "low": 145.00,
    "high": 250.00
  },
  "population": {
    "total": 2847,
    "thisGrade": 412
  }
}
```

## Screen Flow

```
HomeScreen  →  ScanScreen (front)  →  ScanScreen (back)
    ↑                                       ↓
    └──── ResultsScreen  ←  ProcessingScreen (API call)
```

## Permissions

Camera permissions are declared in `app.json` and requested at runtime
via `useCameraPermissions()` in `ScanViewfinder.js`.

- **iOS**: `NSCameraUsageDescription` in `infoPlist`
- **Android**: `android.permission.CAMERA` in `permissions`

## Going to Production

1. Replace all mock data in `ProcessingScreen.js` with your API
2. Set your `bundleIdentifier` (iOS) and `package` (Android) in `app.json`
3. Build: `npx expo build:ios` / `npx expo build:android`
   Or use EAS Build: `npx eas build`
