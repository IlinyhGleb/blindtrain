


const POSE_WRIST_MIN_DX = 0.15;
const POSE_WRIST_MAX_DX = 0.75;
const POSE_TILT_THRESHOLD = 0.30;

function analyzePose(handsList) {
    const sorted = [...handsList].sort((a, b) => a.landmarks[0].x - b.landmarks[0].x);
    const leftInFrame  = sorted[0];
    const rightInFrame = sorted[1];

    if (leftInFrame.label && rightInFrame.label &&
        leftInFrame.label !== 'Left') {
        return 'swapped';
    }

    const dx = Math.abs(rightInFrame.landmarks[0].x - leftInFrame.landmarks[0].x);
    if (dx < POSE_WRIST_MIN_DX) return 'too_close';
    if (dx > POSE_WRIST_MAX_DX) return 'too_far';

    for (const hand of handsList) {
        const wrist = hand.landmarks[0];
        const midTip = hand.landmarks[12];
        const handDx = Math.abs(midTip.x - wrist.x);
        const handDy = Math.abs(midTip.y - wrist.y);
        if (handDy - handDx > POSE_TILT_THRESHOLD) return 'tilted';
    }

    return 'ok';
}




function makeHand(wristX, wristY, midDx = 0.05, midDy = -0.15, label = null) {
    const landmarks = [];
    for (let i = 0; i < 21; i++) landmarks.push({x: 0, y: 0, z: 0});
    landmarks[0] = {x: wristX, y: wristY, z: 0};
    landmarks[12] = {x: wristX + midDx, y: wristY + midDy, z: 0};
    return {landmarks, label};
}



let failed = 0;
function expect(name, got, want) {
    if (got === want) {
        console.log(`OK   ${name}: ${got}`);
    } else {
        console.log(`FAIL ${name}: got ${got}, want ${want}`);
        failed++;
    }
}



expect(
    'normal_pose',
    analyzePose([
        makeHand(0.3, 0.5, 0.05, -0.15, 'Left'),
        makeHand(0.7, 0.5, -0.05, -0.15, 'Right'),
    ]),
    'ok'
);


expect(
    'normal_pose_no_label',
    analyzePose([
        makeHand(0.3, 0.5),
        makeHand(0.7, 0.5),
    ]),
    'ok'
);



expect(
    'swapped_hands',
    analyzePose([
        makeHand(0.3, 0.5, 0.05, -0.15, 'Right'),
        makeHand(0.7, 0.5, -0.05, -0.15, 'Left'),
    ]),
    'swapped'
);


expect(
    'too_close',
    analyzePose([
        makeHand(0.45, 0.5, 0, -0.15, 'Left'),
        makeHand(0.55, 0.5, 0, -0.15, 'Right'),
    ]),
    'too_close'
);


expect(
    'too_far',
    analyzePose([
        makeHand(0.1, 0.5, 0, -0.15, 'Left'),
        makeHand(0.9, 0.5, 0, -0.15, 'Right'),
    ]),
    'too_far'
);


expect(
    'tilted_left_hand',
    analyzePose([
        makeHand(0.3, 0.5, 0.02, -0.40, 'Left'),
        makeHand(0.7, 0.5, -0.05, -0.15, 'Right'),
    ]),
    'tilted'
);


expect(
    'tilted_right_hand',
    analyzePose([
        makeHand(0.3, 0.5, 0.05, -0.15, 'Left'),
        makeHand(0.7, 0.5, 0.02, -0.40, 'Right'),
    ]),
    'tilted'
);



expect(
    'at_min_distance_is_ok',
    analyzePose([
        makeHand(0.3, 0.5, 0.05, -0.15, 'Left'),
        makeHand(0.45, 0.5, -0.05, -0.15, 'Right'),
    ]),
    'ok'
);


expect(
    'swap_has_priority_over_close',
    analyzePose([
        makeHand(0.45, 0.5, 0, -0.15, 'Right'),  
        makeHand(0.55, 0.5, 0, -0.15, 'Left'),
    ]),
    'swapped'
);


expect(
    'swap_has_priority_over_tilt',
    analyzePose([
        makeHand(0.3, 0.5, 0.02, -0.40, 'Right'),
        makeHand(0.7, 0.5, 0.02, -0.40, 'Left'),
    ]),
    'swapped'
);


expect(
    'tilt_at_threshold_is_ok',
    analyzePose([
        makeHand(0.3, 0.5, 0.05, -0.35, 'Left'),  
        makeHand(0.7, 0.5, -0.05, -0.15, 'Right'),
    ]),
    'ok'
);


expect(
    'order_independent',
    analyzePose([
        makeHand(0.7, 0.5, -0.05, -0.15, 'Right'),  
        makeHand(0.3, 0.5, 0.05, -0.15, 'Left'),
    ]),
    'ok'
);

console.log('');
if (failed === 0) {
    console.log('✓ Все тесты пройдены');
    process.exit(0);
} else {
    console.log(`✗ Провалено тестов: ${failed}`);
    process.exit(1);
}
