import Vision
import AppKit
for p in CommandLine.arguments.dropFirst() {
  guard let img = NSImage(contentsOfFile: p), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
  let req = VNDetectFaceRectanglesRequest()
  try? VNImageRequestHandler(cgImage: cg).perform([req])
  if let f = req.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width }) {
    let b = f.boundingBox
    print(p, String(format: "%.3f %.3f %.3f %.3f", b.midX, 1 - b.midY, b.width, b.height))
  }
}
