const MEDIAPIPE_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands';

importScripts(MEDIAPIPE_BASE + '/hands.js');

let hands = null;
let busy = false;
let pendingBitmap = null;
let lastResultForFrame = null;

function initHands() {
    hands = new self.Hands({
        locateFile: (file) => MEDIAPIPE_BASE + '/' + file,
    });
    hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
    });
    hands.onResults((results) => {
        const landmarksList = results.multiHandLandmarks || [];
        const handednessList = results.multiHandedness || [];
        lastResultForFrame = {
            landmarksList: landmarksList.map(lm =>
                lm.map(p => ({ x: p.x, y: p.y, z: p.z }))
            ),
            handedness: handednessList.map(h => ({
                label: h.label,
                score: h.score,
            })),
        };
    });
}

async function processBitmap(bitmap) {
    if (busy) {
        if (pendingBitmap) pendingBitmap.close();
        pendingBitmap = bitmap;
        return;
    }
    busy = true;
    try {
        lastResultForFrame = null;
        await hands.send({ image: bitmap });
        bitmap.close();
        if (lastResultForFrame) {
            self.postMessage({ type: 'results', payload: lastResultForFrame });
        }
    } catch (e) {
        self.postMessage({ type: 'error', message: String(e) });
        try { bitmap.close(); } catch (_) {}
    } finally {
        busy = false;
        if (pendingBitmap) {
            const next = pendingBitmap;
            pendingBitmap = null;
            processBitmap(next);
        }
    }
}

self.onmessage = (e) => {
    const msg = e.data || {};
    if (msg.type === 'init') {
        try {
            initHands();
            self.postMessage({ type: 'ready' });
        } catch (err) {
            self.postMessage({ type: 'error', message: String(err) });
        }
        return;
    }
    if (msg.type === 'frame') {
        if (!hands) return;
        processBitmap(msg.bitmap);
        return;
    }
};
