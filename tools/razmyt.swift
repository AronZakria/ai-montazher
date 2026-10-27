// Где на картинке нужные слова (macOS Vision) — для размытия личных данных.
// razmyt <картинка> <шаблон> [шаблон…]  → строки «x y w h слово» в px от левого верхнего угла.
// Шаблон ищется без учёта регистра внутри распознанных строк; рамка — ровно под найденный кусок.
import AppKit
import Vision

let args = CommandLine.arguments
guard args.count >= 3, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(1) }
let W = Double(cg.width), H = Double(cg.height)
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
req.recognitionLanguages = ["ru-RU", "en-US"]
try? VNImageRequestHandler(cgImage: cg).perform([req])
for obs in req.results ?? [] {
    guard let cand = obs.topCandidates(1).first else { continue }
    let s = cand.string
    for pat in args.dropFirst(2) {
        var from = s.startIndex
        while let r = s.range(of: pat, options: .caseInsensitive, range: from..<s.endIndex) {
            if let b = try? cand.boundingBox(for: r)?.boundingBox {
                print(String(format: "%.0f %.0f %.0f %.0f %@", b.minX * W, (1 - b.maxY) * H, b.width * W, b.height * H, String(s[r])))
            }
            from = r.upperBound
        }
    }
}
