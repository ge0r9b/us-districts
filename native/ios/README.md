# US Districts for iPhone

A small iPhone app that shows the live v2 map at <https://ge0r9b.github.io/us-districts/v2/>. It is one SwiftUI screen with one web view. There are no third-party libraries in the app, so the download stays well under 5 MB.

The web view stays inside the safe area and is locked to light mode, matching the v2 page. Links that leave `ge0r9b.github.io/us-districts/v2` open in Safari. Pages the app has already loaded are saved on the device. The first open needs a connection. After that, the saved copy opens offline. Map tiles and address search still need a connection. If nothing has been saved yet, the app shows a short offline message instead of a blank page.

On an Apple Silicon Mac the same iPhone app runs as **My Mac (Designed for iPhone)**, in an iPhone-sized window. `SUPPORTS_MACCATALYST` is NO. This is not a Mac Catalyst build.

- Display name: US Districts
- Bundle id: `com.ge0r9b.usdistricts`
- Deployment target: iOS 16, iPhone only

GitHub Actions builds the app **unsigned**. Nothing in this repo is a certificate, a profile, or a password. You download the artifact and sign it on your Mac.

## Download the unsigned build

1. Open this repository on GitHub and click the **Actions** tab.
2. Click the **iOS v2** workflow in the left sidebar.
3. Open the latest run for the `native/ios-v2` branch. To start a run yourself, click **Run workflow**, choose `native/ios-v2`, and confirm.
4. When the run is green, scroll to **Artifacts** and download **USDistricts-unsigned**.
5. Unzip that download. It contains:
   - `USDistricts.xcarchive.zip` — the unsigned device archive. Unzip it to get `USDistricts.xcarchive`.
   - `USDistricts-unsigned.ipa` — the same unsigned app, packed as an `.ipa`.
   - `USDistricts-simulator.app.zip` — the unsigned iOS Simulator app.

The build log prints the size of each of those files and the size of the `.app` inside the archive. The app bundle has to be under 5 MB or the build fails.

You do not need a checkout of this repository on your Mac.

To try the simulator build without signing, unzip `USDistricts-simulator.app.zip` and run:

```bash
xcrun simctl install booted USDistricts.app
xcrun simctl launch booted com.ge0r9b.usdistricts
```

## Sign it

Sign the archive with the Apple ID already signed in to Xcode, or with a paid Apple Developer account. A free Apple ID can install the app on your own iPhone (the install expires after about a week). TestFlight, Ad Hoc, and a build other people can keep all need the paid program.

### Xcode Organizer

1. Unzip `USDistricts.xcarchive.zip`.
2. Double-click `USDistricts.xcarchive`. It opens in the Organizer (Window → Organizer → Archives). If it does not appear, drag the `.xcarchive` onto the Organizer window.
3. Select the archive and click **Distribute App**.
4. Choose a method:
   - **Debugging** or **Development** for your own devices, including a free Apple ID.
   - **Ad Hoc** for devices whose UDIDs are already on your team.
   - **App Store Connect** to upload for TestFlight.
5. Select your team. Xcode creates the profile and signs the app.
6. Install a development `.ipa` by dragging it onto the phone in Finder, with Apple Configurator, or from Xcode’s Devices window.

### Command line

Sign in to Xcode with your Apple ID first (Xcode → Settings → Accounts). The Team ID is the 10-character id next to that account. `-allowProvisioningUpdates` uses that login to create a development profile for `com.ge0r9b.usdistricts`.

```bash
unzip USDistricts.xcarchive.zip

cat > export-development.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>method</key>
	<string>development</string>
	<key>signingStyle</key>
	<string>automatic</string>
	<key>teamID</key>
	<string>YOUR_TEAM_ID</string>
</dict>
</plist>
EOF

xcodebuild -exportArchive \
  -archivePath USDistricts.xcarchive \
  -exportPath ./signed \
  -exportOptionsPlist export-development.plist \
  -allowProvisioningUpdates
```

The signed `.ipa` is in `./signed`.

For Ad Hoc, change `development` to `ad-hoc`. For an App Store Connect upload (TestFlight), change it to `app-store-connect`.

You can also sign the `.app` inside the archive directly. The identity name comes from `security find-identity -v -p codesigning`:

```bash
APP="USDistricts.xcarchive/Products/Applications/USDistricts.app"
codesign --force --sign "Apple Development: You (TEAMID)" "$APP"
```

A device will still refuse to launch that bundle until a matching provisioning profile is embedded. Organizer and `xcodebuild -exportArchive` do that for you. Use `codesign` on its own only when you already have the profile to copy into `USDistricts.app/embedded.mobileprovision`.

## Share it

TestFlight is the easiest way to send the app to other people. It needs the $99/yr Apple Developer Program. Upload with Organizer (**Distribute App → App Store Connect**) or with the `app-store-connect` export above, then invite testers in App Store Connect. Testers on Apple Silicon Macs can install that same build from TestFlight; it opens in an iPhone-sized window.

Ad Hoc needs that same paid program, and it needs each device’s UDID registered on the team before you export. A phone that is not on the list cannot install the Ad Hoc build.

On a Mac, a Developer ID certificate plus notarization is needed for other people to open the app. Running it yourself does not need that: open the project, or the signed build, with the destination **My Mac (Designed for iPhone)**.

## Project layout

`project.yml` is the Xcode project. The workflow installs [XcodeGen](https://github.com/yonaskolb/XcodeGen), generates `USDistricts.xcodeproj`, and builds. The generated project is not committed.

To generate it locally:

```bash
brew install xcodegen
cd native/ios
xcodegen generate
open USDistricts.xcodeproj
```

The icon is redrawn from v2’s US silhouette (`v2/data/ctryshape.js`) and the page’s blue `#2563eb` and red `#dc2626`:

```bash
python3 native/ios/tools/make_icon.py
```
