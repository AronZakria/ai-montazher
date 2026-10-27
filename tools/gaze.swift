// Куда смотрит Арон в каждом кадре (macOS Vision): в камеру или вниз/в сторону (читает с экрана).
// gaze <video> [шаг_кадров] → stdout: "t yaw pitch open pupil_dy pupil_dx"
//   yaw/pitch — поворот головы (рад, pitch > 0 — голова вниз), open — раскрытие глаз (высота/ширина глаза),
//   pupil_dy/dx — смещение зрачка от центра глаза в долях размера глаза (dy > 0 — взгляд вниз).
import AVFoundation
import Vision

let args = CommandLine.arguments
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let step = args.count > 2 ? Int(args[2]) ?? 1 : 1
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack!
asset.loadTracks(withMediaType: .video) { t, _ in track = t?.first; sem.signal() }
sem.wait()
let reader = try! AVAssetReader(asset: asset)
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange,
])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()

func box(_ r: VNFaceLandmarkRegion2D?) -> CGRect? {
    guard let r = r, r.pointCount > 0 else { return nil }
    let xs = r.normalizedPoints.map { $0.x }, ys = r.normalizedPoints.map { $0.y }
    return CGRect(x: xs.min()!, y: ys.min()!, width: xs.max()! - xs.min()!, height: ys.max()! - ys.min()!)
}

var i = 0
while let sb = out.copyNextSampleBuffer() {
    defer { i += 1 }
    if i % step != 0 { continue }
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let t = CMSampleBufferGetPresentationTimeStamp(sb).seconds
    let req = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cvPixelBuffer: pb).perform([req])
    guard let f = req.results?.max(by: { $0.boundingBox.width < $1.boundingBox.width }) else {
        print(String(format: "%.3f nan nan nan nan nan", t)); continue
    }
    let yaw = f.yaw?.doubleValue ?? .nan
    let pitch = f.pitch?.doubleValue ?? .nan
    var open = Double.nan, dy = Double.nan, dx = Double.nan
    if let le = box(f.landmarks?.leftEye), let re = box(f.landmarks?.rightEye) {
        open = Double((le.height / max(le.width, 1e-6) + re.height / max(re.width, 1e-6)) / 2)
        if let lp = f.landmarks?.leftPupil?.normalizedPoints.first, let rp = f.landmarks?.rightPupil?.normalizedPoints.first {
            // y в Vision растёт вверх → dy > 0, когда зрачок ниже центра глаза
            let ldy = (le.midY - lp.y) / max(le.height, 1e-6), rdy = (re.midY - rp.y) / max(re.height, 1e-6)
            let ldx = (lp.x - le.midX) / max(le.width, 1e-6), rdx = (rp.x - re.midX) / max(re.width, 1e-6)
            dy = Double((ldy + rdy) / 2); dx = Double((ldx + rdx) / 2)
        }
    }
    print(String(format: "%.3f %.4f %.4f %.4f %.4f %.4f", t, yaw, pitch, open, dy, dx))
}
