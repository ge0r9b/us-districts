import SwiftUI
import UIKit
import WebKit

/// Which addresses may stay inside the web view.
enum PagePolicy {
    static func allows(_ url: URL) -> Bool {
        let scheme = url.scheme?.lowercased() ?? ""
        if scheme == "about" { return true }
        guard onV2(url) else { return false }
        let host = url.host?.lowercased() ?? ""
        if host == MapSite.originHost { return true }
        if host == "127.0.0.1" || host == "localhost" {
            return (url.port ?? 80) == Int(MapSite.proxyPort)
        }
        return false
    }

    static func safariURL(for url: URL) -> URL? {
        let host = url.host?.lowercased() ?? ""
        if host == "127.0.0.1" || host == "localhost" {
            var parts = URLComponents()
            parts.scheme = "https"
            parts.host = MapSite.originHost
            parts.path = url.path.isEmpty ? "/" : url.path
            if let components = URLComponents(url: url, resolvingAgainstBaseURL: false) {
                parts.percentEncodedQuery = components.percentEncodedQuery
            }
            parts.fragment = url.fragment
            return parts.url
        }
        let scheme = url.scheme?.lowercased() ?? ""
        guard scheme == "http" || scheme == "https" else { return nil }
        return url
    }

    private static func onV2(_ url: URL) -> Bool {
        let path = url.path
        return path == MapSite.v2Path || path.hasPrefix(MapSite.v2Path + "/")
    }
}

struct MapWebView: UIViewRepresentable {
    @Binding var offline: Bool
    var reloadToken: Int

    func makeCoordinator() -> Coordinator {
        Coordinator(offline: $offline)
    }

    func makeUIView(context: Context) -> WKWebView {
        let preferences = WKWebpagePreferences()
        preferences.preferredContentMode = .mobile

        let config = WKWebViewConfiguration()
        config.defaultWebpagePreferences = preferences
        config.allowsInlineMediaPlayback = true

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.overrideUserInterfaceStyle = .light
        webView.isOpaque = true
        webView.backgroundColor = MapSite.uiPaper
        webView.underPageBackgroundColor = MapSite.uiPaper
        webView.scrollView.backgroundColor = MapSite.uiPaper
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.indicatorStyle = .black
        webView.scrollView.keyboardDismissMode = .interactive
        webView.allowsBackForwardNavigationGestures = false
        webView.allowsLinkPreview = false

        context.coordinator.appliedReload = reloadToken
        webView.load(URLRequest(url: MapSite.startURL))
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        guard context.coordinator.appliedReload != reloadToken else { return }
        context.coordinator.appliedReload = reloadToken
        webView.load(URLRequest(url: MapSite.startURL))
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        private let offline: Binding<Bool>
        var appliedReload = 0

        init(offline: Binding<Bool>) {
            self.offline = offline
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.cancel)
                return
            }
            if PagePolicy.allows(url) {
                decisionHandler(.allow)
                return
            }
            let mainFrame = navigationAction.targetFrame?.isMainFrame ?? true
            if mainFrame, let safari = PagePolicy.safariURL(for: url) {
                UIApplication.shared.open(safari)
            }
            decisionHandler(.cancel)
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationResponse: WKNavigationResponse,
            decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
        ) {
            if navigationResponse.isForMainFrame,
               let http = navigationResponse.response as? HTTPURLResponse,
               http.statusCode >= 400,
               !CachingProxy.shared.hasCachedPage {
                offline.wrappedValue = true
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            guard let url = navigationAction.request.url else { return nil }
            if PagePolicy.allows(url) {
                webView.load(URLRequest(url: url))
            } else if let safari = PagePolicy.safariURL(for: url) {
                UIApplication.shared.open(safari)
            }
            return nil
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            offline.wrappedValue = false
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            note(error)
        }

        func webView(
            _ webView: WKWebView,
            didFailProvisionalNavigation navigation: WKNavigation!,
            withError error: Error
        ) {
            note(error)
        }

        private func note(_ error: Error) {
            let ns = error as NSError
            if ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled { return }
            if CachingProxy.shared.hasCachedPage { return }
            offline.wrappedValue = true
        }
    }
}
