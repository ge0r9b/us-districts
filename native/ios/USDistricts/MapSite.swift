import SwiftUI
import UIKit

/// Shared addresses and the light colors the v2 map already uses.
enum MapSite {
    static let originHost = "ge0r9b.github.io"
    static let v2Path = "/us-districts/v2"
    static let sitePrefix = "/us-districts"
    static let proxyPort: UInt16 = 47832

    static var startURL: URL {
        URL(string: "http://127.0.0.1:\(proxyPort)\(v2Path)/")!
    }

    static let paper = Color(red: 221 / 255, green: 221 / 255, blue: 221 / 255)
    static let ink = Color(red: 28 / 255, green: 25 / 255, blue: 23 / 255)
    static let muted = Color(red: 87 / 255, green: 83 / 255, blue: 78 / 255)
    static let uiPaper = UIColor(red: 221 / 255, green: 221 / 255, blue: 221 / 255, alpha: 1)
}
