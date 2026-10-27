// Распознаёт текст на картинках встроенным в macOS Vision (офлайн).
// swift tools/ocr.swift img1.jpg img2.jpg …  → JSON {путь: "текст"}
import Foundation
import Vision
import AppKit

var result: [String: String] = [:]
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        result[path] = ""
        continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = ["en-US", "ru-RU"]
    try? VNImageRequestHandler(cgImage: cg).perform([req])
    // сверху вниз, слева направо
    let lines = (req.results ?? [])
        .sorted { a, b in
            abs(a.boundingBox.midY - b.boundingBox.midY) > 0.02
                ? a.boundingBox.midY > b.boundingBox.midY
                : a.boundingBox.minX < b.boundingBox.minX
        }
        .compactMap { $0.topCandidates(1).first?.string }
    result[path] = lines.joined(separator: "\n")
}
let data = try! JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .withoutEscapingSlashes])
print(String(data: data, encoding: .utf8)!)
