import CryptoKit
import Darwin
import Foundation

/// Loopback cache in front of the live v2 site.
///
/// WKWebView will not let the app intercept https, and GitHub Pages marks the
/// map fresh for only ten minutes. This server is the web view's origin for
/// `/us-districts/…`. It stores each full response on disk and serves that
/// copy when the network request fails.
final class CachingProxy: NSObject {
    static let shared = CachingProxy()

    private let cacheDirectory: URL
    private let session: URLSession
    private let lock = NSLock()
    private var listenFD: Int32 = -1

    private override init() {
        let root = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let directory = root.appendingPathComponent("PageCache", isDirectory: true)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        var mutable = directory
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try? mutable.setResourceValues(values)
        cacheDirectory = directory

        let config = URLSessionConfiguration.ephemeral
        config.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        config.urlCache = nil
        config.timeoutIntervalForRequest = 25
        config.timeoutIntervalForResource = 120
        session = URLSession(configuration: config)
        super.init()
    }

    var hasCachedPage: Bool {
        let names = [
            cacheName(for: MapSite.v2Path + "/"),
            cacheName(for: MapSite.v2Path + "/index.html"),
            cacheName(for: MapSite.v2Path)
        ]
        return names.contains { FileManager.default.fileExists(atPath: cacheDirectory.appendingPathComponent($0).path) }
    }

    func start() {
        lock.lock()
        defer { lock.unlock() }
        guard listenFD < 0 else { return }

        let fd = Darwin.socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { return }

        var reuse: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, socklen_t(MemoryLayout<Int32>.size))
        setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &reuse, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = MapSite.proxyPort.bigEndian
        addr.sin_addr.s_addr = UInt32(0x7f000001).bigEndian
        let bound = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bound == 0, Darwin.listen(fd, 32) == 0 else {
            Darwin.close(fd)
            print("US Districts could not listen on 127.0.0.1:\(MapSite.proxyPort)")
            return
        }
        listenFD = fd
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.acceptLoop(fd)
        }
    }

    private func acceptLoop(_ fd: Int32) {
        while true {
            let client = Darwin.accept(fd, nil, nil)
            if client < 0 {
                if errno == EINTR { continue }
                break
            }
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                self?.serve(client)
            }
        }
    }

    private func serve(_ client: Int32) {
        defer { Darwin.close(client) }
        var noSignal: Int32 = 1
        setsockopt(client, SOL_SOCKET, SO_NOSIGPIPE, &noSignal, socklen_t(MemoryLayout<Int32>.size))
        var timeout = timeval()
        timeout.tv_sec = 30
        timeout.tv_usec = 0
        setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, socklen_t(MemoryLayout<timeval>.size))

        guard let raw = readHeaders(client), let request = parse(raw) else {
            writeHTTP(client, status: 400, reason: "Bad Request", mime: "text/plain", body: Data())
            return
        }
        let method = request.method.uppercased()
        guard method == "GET" || method == "HEAD" else {
            writeHTTP(client, status: 405, reason: "Method Not Allowed", mime: "text/plain", body: Data())
            return
        }

        let target = normalize(request.target)
        let path = target.split(separator: "?", maxSplits: 1).first.map(String.init) ?? target
        guard safe(path) else {
            writeHTTP(client, status: 404, reason: "Not Found", mime: "text/plain", body: Data())
            return
        }

        let range = request.headers["range"]
        let upstreamString = "https://\(MapSite.originHost)" + (target.hasPrefix("/") ? target : "/" + target)
        guard let upstream = URL(string: upstreamString) else {
            writeHTTP(client, status: 400, reason: "Bad Request", mime: "text/plain", body: Data())
            return
        }

        let fetched = fetch(upstream, range: range)
        let response: HTTPResult
        if let fetched {
            if range == nil, (200..<300).contains(fetched.status), fetched.status != 206, !fetched.body.isEmpty {
                store(path: path, mime: fetched.mime, body: fetched.body)
            }
            response = HTTPResult(
                status: fetched.status,
                reason: reason(for: fetched.status),
                mime: fetched.mime,
                body: method == "HEAD" ? Data() : fetched.body,
                contentRange: fetched.contentRange
            )
        } else if let cached = load(path) {
            let sliced = slice(cached.body, range: range)
            response = HTTPResult(
                status: sliced.status,
                reason: sliced.status == 206 ? "Partial Content" : "OK",
                mime: cached.mime,
                body: method == "HEAD" ? Data() : sliced.body,
                contentRange: sliced.contentRange
            )
        } else {
            response = HTTPResult(status: 503, reason: "Service Unavailable", mime: "text/plain", body: Data(), contentRange: nil)
        }
        writeHTTP(
            client,
            status: response.status,
            reason: response.reason,
            mime: response.mime,
            body: response.body,
            contentRange: response.contentRange
        )
    }

    private struct HTTPResult {
        var status: Int
        var reason: String
        var mime: String
        var body: Data
        var contentRange: String?
    }

    private func reason(for status: Int) -> String {
        switch status {
        case 200: return "OK"
        case 206: return "Partial Content"
        case 404: return "Not Found"
        default: return "OK"
        }
    }

    private struct Upstream {
        var status: Int
        var mime: String
        var body: Data
        var contentRange: String?
    }

    private func fetch(_ url: URL, range: String?) -> Upstream? {
        var request = URLRequest(url: url)
        request.setValue("USDistricts/1.0", forHTTPHeaderField: "User-Agent")
        if let range {
            request.setValue(range, forHTTPHeaderField: "Range")
        }
        let semaphore = DispatchSemaphore(value: 0)
        var dataOut: Data?
        var responseOut: URLResponse?
        var errorOut: Error?
        session.dataTask(with: request) { data, response, error in
            dataOut = data
            responseOut = response
            errorOut = error
            semaphore.signal()
        }.resume()
        semaphore.wait()
        guard errorOut == nil,
              let http = responseOut as? HTTPURLResponse,
              http.url?.host?.lowercased() == MapSite.originHost,
              let data = dataOut else {
            return nil
        }
        if (500..<600).contains(http.statusCode) {
            return nil
        }
        let mime = http.value(forHTTPHeaderField: "Content-Type") ?? guessedType(url.path)
        return Upstream(
            status: http.statusCode,
            mime: mime,
            body: data,
            contentRange: http.value(forHTTPHeaderField: "Content-Range")
        )
    }

    private func slice(_ body: Data, range: String?) -> (status: Int, body: Data, contentRange: String?) {
        guard let range else { return (200, body, nil) }
        let spec = range.lowercased().hasPrefix("bytes=") ? String(range.dropFirst(6)) : range
        let parts = spec.split(separator: "-", maxSplits: 1, omittingEmptySubsequences: false)
        guard parts.count == 2, let start = Int(parts[0]), start >= 0, start < body.count else {
            return (200, body, nil)
        }
        let requestedEnd = Int(parts[1]) ?? (body.count - 1)
        let end = min(max(requestedEnd, start), body.count - 1)
        let piece = body.subdata(in: start..<(end + 1))
        return (206, piece, "bytes \(start)-\(end)/\(body.count)")
    }

    private func readHeaders(_ fd: Int32) -> String? {
        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 4096)
        let marker = Data("\r\n\r\n".utf8)
        while data.count < 65_536 {
            let count = buffer.withUnsafeMutableBytes { raw -> Int in
                guard let base = raw.baseAddress else { return -1 }
                return Darwin.read(fd, base, raw.count)
            }
            if count <= 0 { break }
            data.append(contentsOf: buffer.prefix(count))
            if data.range(of: marker) != nil { break }
        }
        guard let end = data.range(of: marker) else { return nil }
        return String(data: data.subdata(in: 0..<end.lowerBound), encoding: .utf8)
    }

    private func parse(_ raw: String) -> (method: String, target: String, headers: [String: String])? {
        let lines = raw.components(separatedBy: "\r\n")
        guard let first = lines.first else { return nil }
        let pieces = first.split(separator: " ", maxSplits: 2, omittingEmptySubsequences: true)
        guard pieces.count >= 2 else { return nil }
        var headers: [String: String] = [:]
        for line in lines.dropFirst() {
            guard let colon = line.firstIndex(of: ":") else { continue }
            let name = line[..<colon].trimmingCharacters(in: .whitespaces).lowercased()
            let value = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
            headers[name] = value
        }
        return (String(pieces[0]), String(pieces[1]), headers)
    }

    private func normalize(_ target: String) -> String {
        if target.hasPrefix("http://") || target.hasPrefix("https://"),
           let url = URL(string: target) {
            var path = url.path.isEmpty ? "/" : url.path
            if let query = url.query, !query.isEmpty {
                path += "?" + query
            }
            return path
        }
        return target.hasPrefix("/") ? target : "/" + target
    }

    private func safe(_ path: String) -> Bool {
        let decoded = path.removingPercentEncoding ?? path
        if path.contains("..") || decoded.contains("..") { return false }
        return path == MapSite.sitePrefix || path.hasPrefix(MapSite.sitePrefix + "/")
    }

    private func guessedType(_ path: String) -> String {
        let lower = path.lowercased()
        if lower.hasSuffix(".js") { return "text/javascript; charset=utf-8" }
        if lower.hasSuffix(".css") { return "text/css; charset=utf-8" }
        if lower.hasSuffix(".html") || lower.hasSuffix(".htm") { return "text/html; charset=utf-8" }
        if lower.hasSuffix(".png") { return "image/png" }
        if lower.hasSuffix(".jpg") || lower.hasSuffix(".jpeg") { return "image/jpeg" }
        if lower.hasSuffix(".svg") { return "image/svg+xml" }
        if lower.hasSuffix(".json") { return "application/json" }
        return "application/octet-stream"
    }

    private func cacheName(for path: String) -> String {
        let digest = SHA256.hash(data: Data(path.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    private func store(path: String, mime: String, body: Data) {
        let mimeData = Data(mime.utf8)
        guard mimeData.count < 400 else { return }
        var file = Data()
        let length = UInt32(mimeData.count)
        file.append(UInt8((length >> 24) & 0xff))
        file.append(UInt8((length >> 16) & 0xff))
        file.append(UInt8((length >> 8) & 0xff))
        file.append(UInt8(length & 0xff))
        file.append(mimeData)
        file.append(body)
        let url = cacheDirectory.appendingPathComponent(cacheName(for: path))
        try? file.write(to: url, options: .atomic)
    }

    private func load(_ path: String) -> (mime: String, body: Data)? {
        let url = cacheDirectory.appendingPathComponent(cacheName(for: path))
        guard let data = try? Data(contentsOf: url), data.count > 4 else { return nil }
        let length = (Int(data[0]) << 24) | (Int(data[1]) << 16) | (Int(data[2]) << 8) | Int(data[3])
        guard length > 0, length < 400, data.count >= 4 + length else { return nil }
        let mime = String(data: data.subdata(in: 4..<(4 + length)), encoding: .utf8) ?? guessedType(path)
        return (mime, data.subdata(in: (4 + length)..<data.count))
    }

    private func writeHTTP(
        _ fd: Int32,
        status: Int,
        reason: String,
        mime: String,
        body: Data,
        contentRange: String? = nil
    ) {
        var head = "HTTP/1.1 \(status) \(reason)\r\n"
        head += "Content-Type: \(mime)\r\n"
        head += "Content-Length: \(body.count)\r\n"
        head += "Cache-Control: no-store\r\n"
        head += "Connection: close\r\n"
        if let contentRange {
            head += "Content-Range: \(contentRange)\r\n"
        }
        head += "\r\n"
        var bytes = Data(head.utf8)
        bytes.append(body)
        bytes.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { return }
            var sent = 0
            while sent < raw.count {
                let wrote = Darwin.write(fd, base.advanced(by: sent), raw.count - sent)
                if wrote <= 0 { return }
                sent += wrote
            }
        }
    }
}
