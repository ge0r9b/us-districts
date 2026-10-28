#!/bin/bash
# Builds an unsigned iPhone app and an unsigned simulator app.
# Run from native/ios after `xcodegen generate`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "---- build settings ----"
SETTINGS="$(xcodebuild \
  -project USDistricts.xcodeproj \
  -scheme USDistricts \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -showBuildSettings)"
# A pipe into grep -q can raise SIGPIPE under pipefail, so match in the shell.
SETTINGS="${SETTINGS}"$'\n'
require_setting() {
  case "$SETTINGS" in
    *"$1"$'\n'*) ;;
    *) echo "error: build settings missing: $1"; exit 1 ;;
  esac
}
first_match() {
  (
    set +o pipefail
    find "$@" -print | head -1
  )
}
require_setting 'SUPPORTS_MACCATALYST = NO'
require_setting 'SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = YES'
require_setting 'TARGETED_DEVICE_FAMILY = 1'
require_setting 'PRODUCT_BUNDLE_IDENTIFIER = com.ge0r9b.usdistricts'
echo "SUPPORTS_MACCATALYST = NO"
echo "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = YES"
echo "TARGETED_DEVICE_FAMILY = 1"

SIGN=(
  CODE_SIGNING_ALLOWED=NO
  CODE_SIGNING_REQUIRED=NO
  CODE_SIGN_IDENTITY=
  DEVELOPMENT_TEAM=
  AD_HOC_CODE_SIGNING_ALLOWED=YES
  COMPILER_INDEX_STORE_ENABLE=NO
)

ARCH="$ROOT/build/USDistricts.xcarchive"
rm -rf "$ARCH"

echo "---- device archive ----"
set +e
xcodebuild \
  -project "$ROOT/USDistricts.xcodeproj" \
  -scheme USDistricts \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$ARCH" \
  archive \
  "${SIGN[@]}"
archive_status=$?
set -e

pack_archive_from_app() {
  local app_src="$1"
  local dsym_src="${2:-}"
  rm -rf "$ARCH"
  mkdir -p "$ARCH/Products/Applications"
  cp -R "$app_src" "$ARCH/Products/Applications/"
  if [ -n "$dsym_src" ] && [ -d "$dsym_src" ]; then
    mkdir -p "$ARCH/dSYMs"
    cp -R "$dsym_src" "$ARCH/dSYMs/"
  fi
  local created
  created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat > "$ARCH/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>ArchiveVersion</key>
	<integer>2</integer>
	<key>ApplicationProperties</key>
	<dict>
		<key>ApplicationPath</key>
		<string>Applications/USDistricts.app</string>
		<key>Architectures</key>
		<array>
			<string>arm64</string>
		</array>
		<key>CFBundleIdentifier</key>
		<string>com.ge0r9b.usdistricts</string>
		<key>CFBundleShortVersionString</key>
		<string>1.0.0</string>
		<key>CFBundleVersion</key>
		<string>1</string>
		<key>SigningIdentity</key>
		<string></string>
		<key>Team</key>
		<string></string>
	</dict>
	<key>CreationDate</key>
	<date>${created}</date>
	<key>Name</key>
	<string>US Districts</string>
	<key>SchemeName</key>
	<string>USDistricts</string>
</dict>
</plist>
EOF
}

if [ "$archive_status" -ne 0 ] || [ ! -d "$ARCH/Products/Applications/USDistricts.app" ]; then
  echo "xcodebuild archive did not produce an app (status ${archive_status}). Building unsigned and packing the archive."
  DD="$ROOT/build/device-derived"
  rm -rf "$DD"
  xcodebuild \
    -project "$ROOT/USDistricts.xcodeproj" \
    -scheme USDistricts \
    -configuration Release \
    -sdk iphoneos \
    -destination 'generic/platform=iOS' \
    -derivedDataPath "$DD" \
    build \
    "${SIGN[@]}"
  APP_SRC="$(first_match "$DD/Build/Products/Release-iphoneos" -maxdepth 1 -type d -name 'USDistricts.app')"
  if [ -z "$APP_SRC" ]; then
    echo "error: device build did not produce USDistricts.app"
    exit 1
  fi
  DSYM_SRC="$(first_match "$DD/Build/Products/Release-iphoneos" -maxdepth 1 -type d -name 'USDistricts.app.dSYM' || true)"
  pack_archive_from_app "$APP_SRC" "$DSYM_SRC"
fi

APP="$ARCH/Products/Applications/USDistricts.app"
if [ ! -d "$APP" ]; then
  echo "error: archive is missing USDistricts.app"
  exit 1
fi

echo "---- built Info.plist ----"
plutil -p "$APP/Info.plist"
test "$(plutil -extract CFBundleDisplayName raw "$APP/Info.plist")" = "US Districts"
test "$(plutil -extract CFBundleIdentifier raw "$APP/Info.plist")" = "com.ge0r9b.usdistricts"
test "$(plutil -extract UIUserInterfaceStyle raw "$APP/Info.plist")" = "Light"
# UIDeviceFamily is a single integer when only iPhone is targeted.
FAMILY="$(plutil -extract UIDeviceFamily xml1 -o - "$APP/Info.plist")"
case "$FAMILY" in
  *'<integer>1</integer>'*) ;;
  *) echo "error: app is not iPhone-only"; echo "$FAMILY"; exit 1 ;;
esac
case "$FAMILY" in
  *'<integer>2</integer>'*) echo "error: iPad (device family 2) is in the app"; exit 1 ;;
esac

echo "---- simulator ----"
SIMDD="$ROOT/build/sim-derived"
rm -rf "$SIMDD"
xcodebuild \
  -project "$ROOT/USDistricts.xcodeproj" \
  -scheme USDistricts \
  -configuration Release \
  -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$SIMDD" \
  build \
  "${SIGN[@]}"
SIM_APP="$(first_match "$SIMDD/Build/Products/Release-iphonesimulator" -maxdepth 1 -type d -name 'USDistricts.app')"
if [ -z "$SIM_APP" ]; then
  echo "error: simulator build did not produce USDistricts.app"
  exit 1
fi

OUT="$ROOT/build/out"
rm -rf "$OUT"
mkdir -p "$OUT"

STAGE="$(mktemp -d)"
mkdir -p "$STAGE/Payload"
cp -R "$APP" "$STAGE/Payload/"
ditto -c -k --keepParent "$STAGE/Payload" "$OUT/USDistricts-unsigned.ipa"
rm -rf "$STAGE"

ditto -c -k --keepParent "$ARCH" "$OUT/USDistricts.xcarchive.zip"
ditto -c -k --keepParent "$SIM_APP" "$OUT/USDistricts-simulator.app.zip"

echo "---- ipa contents ----"
unzip -l "$OUT/USDistricts-unsigned.ipa"

app_bytes() {
  find "$1" -type f -exec stat -f%z {} + | awk '{s+=$1} END {print s+0}'
}

DEVICE_BYTES="$(app_bytes "$APP")"
SIM_BYTES="$(app_bytes "$SIM_APP")"
IPA_BYTES="$(stat -f%z "$OUT/USDistricts-unsigned.ipa")"
ARCH_ZIP_BYTES="$(stat -f%z "$OUT/USDistricts.xcarchive.zip")"
SIM_ZIP_BYTES="$(stat -f%z "$OUT/USDistricts-simulator.app.zip")"

echo "---- sizes ----"
echo "device app bytes ${DEVICE_BYTES}"
echo "simulator app bytes ${SIM_BYTES}"
echo "ipa bytes ${IPA_BYTES}"
echo "xcarchive zip bytes ${ARCH_ZIP_BYTES}"
echo "simulator zip bytes ${SIM_ZIP_BYTES}"
du -h "$APP" "$SIM_APP" "$OUT/USDistricts-unsigned.ipa" "$OUT/USDistricts.xcarchive.zip" "$OUT/USDistricts-simulator.app.zip"

LIMIT=$((5 * 1024 * 1024))
if [ "$DEVICE_BYTES" -ge "$LIMIT" ] || [ "$SIM_BYTES" -ge "$LIMIT" ]; then
  echo "error: app bundle is not under 5 MB"
  exit 1
fi

echo "unsigned build ok"
