import SwiftUI

struct ContentView: View {
    @State private var offline = false
    @State private var reloadToken = 0

    var body: some View {
        ZStack {
            MapSite.paper.ignoresSafeArea()
            MapWebView(offline: $offline, reloadToken: reloadToken)
                .ignoresSafeArea(.keyboard)
            if offline {
                offlineCover
            }
        }
        .preferredColorScheme(.light)
    }

    private var offlineCover: some View {
        ZStack {
            MapSite.paper.ignoresSafeArea()
            VStack(spacing: 18) {
                Text("You're offline")
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(MapSite.ink)
                Text("No saved copy of the map is on this device yet. Connect to the internet and open US Districts once. It will open offline after that.")
                    .font(.body)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(MapSite.muted)
                Button(action: retry) {
                    Text("Try Again")
                        .font(.body.weight(.semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 22)
                        .padding(.vertical, 12)
                        .background(MapSite.ink, in: Capsule())
                }
                .buttonStyle(.plain)
                .padding(.top, 4)
            }
            .padding(32)
            .frame(maxWidth: 420)
        }
    }

    private func retry() {
        offline = false
        reloadToken += 1
    }
}
