import SwiftUI

@main
struct USDistrictsApp: App {
    init() {
        CachingProxy.shared.start()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
