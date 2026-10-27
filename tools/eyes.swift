// Положение глаз в каждом кадре видео (macOS Vision).
// eyes <video> [шаг_кадров]  →  stdout: "t x y" — середина между глазами в долях кадра (y сверху).
// Поворот из файла учитывается (телефон, снятый вертикально, хранит кадр лёжа + флаг поворота):
// доли — от кадра, как его показывают плеер и ffmpeg.
import AVFoundation
import Vision

let args = CommandLine.arguments
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let step = args.count > 2 ? Int(args[2]) ?? 1 : 1
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack!
asset.loadTracks(withMediaType: .video) { t, _ in track = t?.first; sem.signal() }
sem.wait()

// поворот кадра при показе → ориентация для Vision; без неё лицо лежит на боку, а доли — от лежачего кадра
// (2026-10-13, IMG_9754.mov с фронтальной камеры: a=0 b=-1 c=1 d=0 → .left)
let tf = track.preferredTransform
var orient = CGImagePropertyOrientation.up
if tf.a == 0 && tf.b == 1 && tf.c == -1 && tf.d == 0 { orient = .right }
else if tf.a == 0 && tf.b == -1 && tf.c == 1 && tf.d == 0 { orient = .left }
else if tf.a == -1 && tf.b == 0 && tf.c == 0 && tf.d == -1 { orient = .down }

let reader = try! AVAssetReader(asset: asset)
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange,
])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()

var i = 0
while let sb = out.copyNextSampleBuffer() {
    defer { i += 1 }
    if i % step != 0 { continue }
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let t = CMSampleBufferGetPresentationTimeStamp(sb).seconds
    let req = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cvPixelBuffer: pb, orientation: orient).perform([req])
    guard let f = req.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width }) else { continue }
    let b = f.boundingBox
    var pts: [CGPoint] = []
    for eye in [f.landmarks?.leftPupil, f.landmarks?.rightPupil, f.landmarks?.leftEye, f.landmarks?.rightEye] {
        if let e = eye, e.pointCount > 0 { pts += e.normalizedPoints }
    }
    // точки landmarks — в долях рамки лица; переводим в доли кадра
    var x = Double(b.midX), y = Double(b.midY + b.height * 0.15)
    if !pts.isEmpty {
        let n = Double(pts.count)
        let mx = pts.reduce(0.0) { $0 + Double($1.x) } / n
        let my = pts.reduce(0.0) { $0 + Double($1.y) } / n
        x = Double(b.minX) + mx * Double(b.width)
        y = Double(b.minY) + my * Double(b.height)
    }
    print(String(format: "%.4f %.4f %.4f", t, x, 1 - y))
}
